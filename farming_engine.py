import mss
import numpy as np
from PIL import Image
import time
import threading
import math
from pynput.keyboard import Key, Controller

class FarmingEngine:
    def __init__(self, on_position_update=None, on_boundary_warning=None):
        self.on_position_update = on_position_update
        self.on_boundary_warning = on_boundary_warning
        
        self.running = False
        self.farming_thread = None
        self.lock = threading.Lock()
        
        self.sct = None
        self.keyboard_controller = Controller()
        
        # Mini harita koordinatları
        self.minimap_region = None  # {"x": int, "y": int, "width": int, "height": int}
        
        # Daire parametreleri (mini harita koordinatlarında)
        self.circle_center = None  # {"x": int, "y": int}
        self.circle_radius = None  # int (pixel)
        
        # Karakter pozisyonu (mini harita koordinatlarında)
        self.current_position = None  # {"x": int, "y": int}
        
        # Pozisyon tracking (çoklu frame)
        self.position_history = []  # Son N pozisyon
        self.max_history_size = 5
        self.last_detected_position = None
        
        # Dairesel hareket için açı takibi
        self.circle_angle = 0.0  # Radyan cinsinden açı (0-2π)
        self.circle_angle_speed = 0.1  # Her frame'de açı artışı (radyan) - daha yavaş ve smooth dairesel hareket
        self.circle_radius_offset = 0.7  # Merkezden uzaklık (yarıçapın %70'i) - daire çevresinde dolaş
        self.circular_movement_active = False  # Dairesel hareket aktif mi?
        
        # Hareket ayarları
        self.movement_check_interval = 0.05  # saniye (daha sık kontrol)
        self.movement_duration = 0.15  # tuş basma süresi (saniye)
        self.boundary_threshold = 0.85  # yarıçapın %85'ine yaklaştığında uyar
        self.last_movement_time = 0
        self.movement_cooldown = 0.05  # minimum hareket aralığı (daha responsive)
    
    def set_minimap_region(self, x, y, width, height):
        """Mini harita bölgesini ayarla"""
        with self.lock:
            self.minimap_region = {
                "x": x,
                "y": y,
                "width": width,
                "height": height
            }
    
    def set_circle(self, center_x, center_y, radius):
        """Daire parametrelerini ayarla (mini harita koordinatlarında)"""
        with self.lock:
            self.circle_center = {"x": center_x, "y": center_y}
            self.circle_radius = radius
    
    def capture_minimap(self):
        """Mini harita görüntüsünü yakala"""
        if self.sct is None:
            self.sct = mss.mss()
        
        with self.lock:
            if self.minimap_region is None:
                return None
            region = self.minimap_region.copy()
        
        monitor = {
            "top": region["y"],
            "left": region["x"],
            "width": region["width"],
            "height": region["height"]
        }
        
        screenshot = self.sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return np.array(img)
    
    def detect_character_marker(self, minimap_image):
        """Mini haritada karakter işaretçisini (beyaz ok/nokta) tespit et - iyileştirilmiş algoritma"""
        if minimap_image is None:
            return self.last_detected_position
        
        height, width = minimap_image.shape[:2]
        
        # RGB kanallarını ayır
        r, g, b = minimap_image[:, :, 0], minimap_image[:, :, 1], minimap_image[:, :, 2]
        
        # Parlaklık hesabı
        brightness = (r.astype(float) + g.astype(float) + b.astype(float)) / 3
        
        # Beyaz/parlak renk tespiti - karakter marker için optimize edildi
        # Karakter marker genellikle çok parlak beyaz (RGB > 220)
        white_threshold = 220  # Daha yüksek threshold (sadece çok parlak noktalar)
        brightness_mask = brightness > white_threshold
        
        # RGB dengeli olmalı (r≈g≈b) - karakter marker için daha sıkı kontrol
        color_balance_threshold = 25  # Daha sıkı (beyaz için)
        is_balanced = (np.abs(r.astype(float) - g.astype(float)) < color_balance_threshold) & \
                      (np.abs(g.astype(float) - b.astype(float)) < color_balance_threshold) & \
                      (np.abs(r.astype(float) - b.astype(float)) < color_balance_threshold)
        
        white_mask = brightness_mask & is_balanced
        
        # Eğer çok az beyaz piksel varsa, threshold'u düşür (fallback)
        if np.sum(white_mask) < 5:
            white_threshold = 180  # Daha düşük threshold dene
            brightness_mask = brightness > white_threshold
            white_mask = brightness_mask & is_balanced
        
        # Eğer beyaz bulunamazsa, en parlak noktaları kontrol et
        if not np.any(white_mask):
            # Top 5 en parlak noktayı bul
            flat_brightness = brightness.flatten()
            top_indices = np.argsort(flat_brightness)[-5:]
            top_coords = [np.unravel_index(idx, brightness.shape) for idx in top_indices]
            
            # En parlak noktayı al (fallback)
            if len(top_coords) > 0:
                best_y, best_x = top_coords[-1]
                position = {"x": int(best_x), "y": int(best_y)}
                self._add_to_history(position)
                return position
            else:
                return self.last_detected_position
        
        # Beyaz piksellerin blob'larını bul (basit connected components)
        blobs = self._find_blobs(white_mask)
        
        if not blobs:
            return self.last_detected_position
        
        # Her blob'un özelliklerini hesapla
        best_blob = None
        best_score = -1
        
        for blob_mask in blobs:
            blob_pixels = np.sum(blob_mask)
            
            # Çok küçük veya çok büyük blob'ları filtrele
            if blob_pixels < 2 or blob_pixels > 100:
                continue
            
            # Blob'un merkez koordinatları
            y_coords, x_coords = np.where(blob_mask)
            center_x = int(np.mean(x_coords))
            center_y = int(np.mean(y_coords))
            
            # Blob'un ortalama parlaklığı
            blob_brightness = np.mean(brightness[blob_mask])
            
            # Ok şekli skoru (merkez noktası çevresinde yoğunluk kontrolü)
            shape_score = self._calculate_shape_score(minimap_image, center_x, center_y, blob_mask)
            
            # Toplam skor
            score = blob_brightness * 0.7 + shape_score * 0.3
            
            if score > best_score:
                best_score = score
                best_blob = {"x": center_x, "y": center_y, "mask": blob_mask}
        
        if best_blob:
            position = {"x": best_blob["x"], "y": best_blob["y"]}
            # Ok ucunu bul (ok şeklinde ise)
            tip_position = self._find_arrow_tip(minimap_image, best_blob["mask"], best_blob["x"], best_blob["y"])
            if tip_position:
                position = tip_position
            
            self.last_detected_position = position
            self._add_to_history(position)
            return position
        
        return self.last_detected_position
    
    def _find_blobs(self, mask):
        """Basit blob detection (connected components) - scipy olmadan"""
        height, width = mask.shape
        visited = np.zeros_like(mask, dtype=bool)
        blobs = []
        
        def flood_fill(start_y, start_x):
            """BFS ile connected component bul"""
            if visited[start_y, start_x] or not mask[start_y, start_x]:
                return None
            
            blob_mask = np.zeros_like(mask, dtype=bool)
            stack = [(start_y, start_x)]
            
            while stack:
                y, x = stack.pop()
                if visited[y, x] or not mask[y, x]:
                    continue
                
                visited[y, x] = True
                blob_mask[y, x] = True
                
                # 8-connectivity
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < height and 0 <= nx < width:
                            if not visited[ny, nx] and mask[ny, nx]:
                                stack.append((ny, nx))
            
            return blob_mask if np.any(blob_mask) else None
        
        # Tüm blob'ları bul
        for y in range(height):
            for x in range(width):
                if mask[y, x] and not visited[y, x]:
                    blob = flood_fill(y, x)
                    if blob is not None:
                        blobs.append(blob)
        
        return blobs
    
    def _calculate_shape_score(self, image, center_x, center_y, mask):
        """Ok şekli skorunu hesapla - merkez nokta çevresinde yoğunluk analizi"""
        height, width = image.shape[:2]
        
        # Merkez nokta çevresinde küçük bir bölge kontrol et
        radius = 3
        x_min = max(0, center_x - radius)
        x_max = min(width, center_x + radius)
        y_min = max(0, center_y - radius)
        y_max = min(height, center_y + radius)
        
        region_mask = mask[y_min:y_max, x_min:x_max]
        density = np.sum(region_mask) / (region_mask.size + 1)
        
        return density * 100
    
    def _find_arrow_tip(self, image, mask, center_x, center_y):
        """Ok ucunu bul - ok şeklinde ise en uç noktayı döndür"""
        y_coords, x_coords = np.where(mask)
        
        if len(x_coords) < 3:
            return None
        
        # Merkez noktadan en uzak noktayı bul (ok ucu olabilir)
        distances = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
        max_idx = np.argmax(distances)
        
        tip_x = int(x_coords[max_idx])
        tip_y = int(y_coords[max_idx])
        
        return {"x": tip_x, "y": tip_y}
    
    def _add_to_history(self, position):
        """Pozisyon geçmişine ekle ve stabilizasyon uygula"""
        if position is None:
            return
        
        self.position_history.append(position)
        if len(self.position_history) > self.max_history_size:
            self.position_history.pop(0)
    
    def _get_stabilized_position(self):
        """Pozisyon geçmişinden stabilize edilmiş pozisyon al"""
        if not self.position_history:
            return self.last_detected_position
        
        # Son pozisyonları ortala (gürültüyü azalt)
        if len(self.position_history) >= 3:
            recent = self.position_history[-3:]
            avg_x = int(np.mean([p["x"] for p in recent]))
            avg_y = int(np.mean([p["y"] for p in recent]))
            return {"x": avg_x, "y": avg_y}
        
        return self.position_history[-1]
    
    def is_inside_circle(self, position, center, radius):
        """Pozisyonun daire içinde olup olmadığını kontrol et"""
        if position is None or center is None or radius is None:
            return False
        
        dx = position["x"] - center["x"]
        dy = position["y"] - center["y"]
        distance = math.sqrt(dx * dx + dy * dy)
        
        return distance <= radius
    
    def get_distance_to_center(self, position, center):
        """Merkeze olan uzaklığı hesapla"""
        if position is None or center is None:
            return float('inf')
        
        dx = position["x"] - center["x"]
        dy = position["y"] - center["y"]
        return math.sqrt(dx * dx + dy * dy)
    
    def calculate_direction_to_center(self, position, center):
        """Merkeze doğru yönü hesapla (W A S D kombinasyonu)"""
        if position is None or center is None:
            return []
        
        dx = center["x"] - position["x"]
        dy = center["y"] - position["y"]
        
        # Mini haritada: y ekseni ters (yukarı = küçük y)
        # W = yukarı, S = aşağı, A = sol, D = sağ
        keys = []
        
        # Yatay hareket
        if abs(dx) > 5:
            if dx > 0:
                keys.append('d')  # Sağa
            else:
                keys.append('a')  # Sola
        
        # Dikey hareket
        if abs(dy) > 5:
            if dy > 0:
                keys.append('s')  # Aşağı
            else:
                keys.append('w')  # Yukarı
        
        return keys if keys else ['w']  # Varsayılan: ileri
    
    def calculate_circular_movement_direction(self, position, center, radius):
        """Daire içinde dairesel hareket için yön hesapla - optimize edilmiş"""
        if position is None or center is None or radius is None:
            return []
        
        # Mevcut pozisyonun merkeze göre açısını ve mesafesini hesapla
        dx_current = position["x"] - center["x"]
        dy_current = position["y"] - center["y"]
        current_distance = math.sqrt(dx_current**2 + dy_current**2)
        
        # Eğer açı başlatılmamışsa, mevcut pozisyondan başlat
        if not self.circular_movement_active or self.circle_angle == 0.0:
            if dx_current != 0 or dy_current != 0:
                self.circle_angle = math.atan2(dy_current, dx_current)
            self.circular_movement_active = True
        
        # Hedef pozisyonu hesapla (dairenin çevresinde, mevcut açıdan ileride)
        target_distance = radius * self.circle_radius_offset
        target_x = center["x"] + target_distance * math.cos(self.circle_angle)
        target_y = center["y"] + target_distance * math.sin(self.circle_angle)
        
        # Mevcut pozisyondan hedefe doğru yön hesapla
        dx = target_x - position["x"]
        dy = target_y - position["y"]
        distance_to_target = math.sqrt(dx**2 + dy**2)
        
        # Açıyı sürekli güncelle (dairesel hareket için)
        self.circle_angle += self.circle_angle_speed
        if self.circle_angle >= 2 * math.pi:
            self.circle_angle -= 2 * math.pi
        
        # Eğer hedefe çok yakınsa (5 pixel içinde), yavaşça hareket et
        if distance_to_target < 5:
            # Açı güncellendi, minimal hareket yap
            keys = []
            if abs(dx) > 1:
                keys.append('d' if dx > 0 else 'a')
            if abs(dy) > 1:
                keys.append('s' if dy > 0 else 'w')
            return keys if keys else ['w']  # Minimal hareket
        
        keys = []
        
        # Yatay hareket - threshold optimize edildi
        if abs(dx) > 3:
            if dx > 0:
                keys.append('d')  # Sağa
            else:
                keys.append('a')  # Sola
        
        # Dikey hareket
        if abs(dy) > 3:
            if dy > 0:
                keys.append('s')  # Aşağı
            else:
                keys.append('w')  # Yukarı
        
        # Eğer hiç tuş yoksa, varsayılan olarak ileri git
        return keys if keys else ['w']
    
    def press_keys(self, keys):
        """W A S D tuşlarına bas"""
        if not keys:
            return
        
        try:
            # Tuşları basılı tut
            for key in keys:
                self.keyboard_controller.press(key)
            
            # Belirlenen süre kadar bekle
            time.sleep(self.movement_duration)
            
            # Tuşları bırak
            for key in keys:
                self.keyboard_controller.release(key)
            
        except Exception as e:
            print(f"Tuş basma hatası: {e}")
    
    def _farming_loop(self):
        """Ana farming döngüsü"""
        # MSS nesnesini bu thread'de oluştur
        self.sct = mss.mss()
        
        while self.running:
            try:
                # Mini harita görüntüsünü yakala
                minimap_image = self.capture_minimap()
                
                if minimap_image is None:
                    time.sleep(0.5)
                    continue
                
                # Karakter pozisyonunu tespit et - mini haritadan marker takibi
                position = self.detect_character_marker(minimap_image)
                
                # Stabilize edilmiş pozisyon kullan (gürültüyü azalt)
                if position:
                    stabilized_position = self._get_stabilized_position()
                    if stabilized_position:
                        position = stabilized_position
                else:
                    # Marker bulunamazsa, son bilinen pozisyonu kullan
                    position = self.last_detected_position
                
                with self.lock:
                    self.current_position = position
                    circle_center = self.circle_center.copy() if self.circle_center else None
                    circle_radius = self.circle_radius
                
                if position is None or circle_center is None or circle_radius is None:
                    time.sleep(self.movement_check_interval)
                    continue
                
                # Pozisyon güncellemesi - UI'ya bildir
                if self.on_position_update and position:
                    try:
                        self.on_position_update(position, circle_center, circle_radius)
                    except Exception as e:
                        print(f"Position update callback hatası: {e}")
                
                # Daire içinde mi kontrol et - sürekli kontrol ve marker takibi
                distance = self.get_distance_to_center(position, circle_center)
                is_inside = distance <= circle_radius
                
                # Sınır kontrolü (yarıçapın %85'ine yaklaştı mı?)
                boundary_distance = circle_radius * self.boundary_threshold
                
                current_time = time.time()
                
                if distance > circle_radius:
                    # Daire dışında, merkeze doğru yönlen - marker takibi ile
                    self.circular_movement_active = False  # Dairesel hareketi durdur
                    
                    if current_time - self.last_movement_time >= self.movement_cooldown:
                        direction = self.calculate_direction_to_center(position, circle_center)
                        if direction:  # Yön varsa hareket et
                            self.press_keys(direction)
                            self.last_movement_time = current_time
                            
                            # Marker takibi: pozisyon güncellendi mi kontrol et
                        if self.on_boundary_warning:
                            try:
                                self.on_boundary_warning(
                                    f"Daire dışı! Mesafe: {distance:.1f}/{circle_radius}, Merkeze yönleniyor...",
                                    distance, circle_radius
                                )
                            except:
                                # Callback signature uyumsuzluğu için fallback
                                self.on_boundary_warning(distance, circle_radius, direction)
                        
                        # Açıyı merkeze göre ayarla (merkeze döndükten sonra yeniden başla)
                        dx = circle_center["x"] - position["x"]
                        dy = circle_center["y"] - position["y"]
                        if dx != 0 or dy != 0:
                            self.circle_angle = math.atan2(dy, dx)
                
                elif distance > boundary_distance:
                    # Sınır yakınında, merkeze doğru yönlen - marker takibi ile
                    self.circular_movement_active = False
                    
                    if current_time - self.last_movement_time >= self.movement_cooldown:
                        direction = self.calculate_direction_to_center(position, circle_center)
                        if direction:
                            self.press_keys(direction)
                            self.last_movement_time = current_time
                            
                            # Marker takibi: sınır uyarısı
                            if self.on_boundary_warning:
                                try:
                                    self.on_boundary_warning(
                                        f"Sınır yakını! Mesafe: {distance:.1f}/{boundary_distance:.1f}, Merkeze yönleniyor...",
                                        distance, circle_radius
                                    )
                                except:
                                    # Callback signature uyumsuzluğu için fallback
                                    self.on_boundary_warning(distance, circle_radius, direction)
                
                else:
                    # Daire içinde, dairesel hareket - sürekli kontrol ve marker takibi
                    if current_time - self.last_movement_time >= self.movement_cooldown:
                        # Dairesel hareket için yön hesapla
                        direction = self.calculate_circular_movement_direction(
                            position, circle_center, circle_radius
                        )
                        
                        # Eğer yön varsa hareket et
                        if direction:
                            self.press_keys(direction)
                            self.last_movement_time = current_time
                        else:
                            # Yön yoksa bile kısa bir bekleme yap (sürekli kontrol için)
                            self.last_movement_time = current_time - (self.movement_cooldown * 0.5)
                
                # Sürekli kontrol için kısa bekleme
                time.sleep(self.movement_check_interval)
                
            except Exception as e:
                if self.on_boundary_warning:
                    self.on_boundary_warning(0, 0, f"Hata: {e}")
                time.sleep(1)
    
    def start(self):
        """Farming modunu başlat"""
        with self.lock:
            if not self.running:
                if self.minimap_region is None or self.circle_center is None or self.circle_radius is None:
                    return False, "Mini harita bölgesi veya daire ayarlanmamış"
                
                self.running = True
                self.farming_thread = threading.Thread(target=self._farming_loop, daemon=True)
                self.farming_thread.start()
                return True, "Farming modu başlatıldı"
            return False, "Farming modu zaten çalışıyor"
    
    def stop(self):
        """Farming modunu durdur"""
        self.running = False
        if self.farming_thread:
            self.farming_thread.join(timeout=2.0)
    
    def get_status(self):
        """Mevcut durumu döndür"""
        with self.lock:
            return {
                'running': self.running,
                'position': self.current_position,
                'circle_center': self.circle_center,
                'circle_radius': self.circle_radius,
                'minimap_region': self.minimap_region
            }

