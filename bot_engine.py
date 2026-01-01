import mss
import numpy as np
from PIL import Image
import time
import json
import threading
from pynput.keyboard import Key, Controller

class DiabloImmortalBotEngine:
    def __init__(self, config_path="config.json", on_hp_update=None, on_potion_used=None, on_debug_image=None):
        self.config_path = config_path
        self.on_hp_update = on_hp_update
        self.on_potion_used = on_potion_used
        self.debug_image_callback = on_debug_image
        
        self.running = False
        self.bot_thread = None
        self.lock = threading.Lock()
        
        # MSS nesnesi thread-local olacak, bot thread'inde oluşturulacak
        self.sct = None
        self.keyboard_controller = Controller()
        self.last_potion_time = 0
        self.potion_count = 0
        self.debug_image_callback = None
        
        self.load_config()
    
    def load_config(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        with self.lock:
            self.hp_bar = self.config['hp_bar'].copy()
            self.hp_colors = self.config['hp_colors'].copy()
            self.hp_threshold = self.config['hp_threshold']
            self.key_to_press = self.config['key_to_press']
            self.check_interval = self.config['check_interval_ms'] / 1000.0
            self.cooldown = self.config['cooldown_ms'] / 1000.0
            self.key_press_duration = self.config.get('key_press_duration_ms', 60) / 1000.0
    
    def save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def update_config(self, **kwargs):
        with self.lock:
            if 'hp_bar' in kwargs:
                self.hp_bar = kwargs['hp_bar'].copy()
                self.config['hp_bar'] = kwargs['hp_bar']
            if 'hp_colors' in kwargs:
                self.hp_colors = kwargs['hp_colors'].copy()
                self.config['hp_colors'] = kwargs['hp_colors']
            if 'hp_threshold' in kwargs:
                self.hp_threshold = kwargs['hp_threshold']
                self.config['hp_threshold'] = kwargs['hp_threshold']
            if 'key_to_press' in kwargs:
                self.key_to_press = kwargs['key_to_press']
                self.config['key_to_press'] = kwargs['key_to_press']
            if 'check_interval_ms' in kwargs:
                self.check_interval = kwargs['check_interval_ms'] / 1000.0
                self.config['check_interval_ms'] = kwargs['check_interval_ms']
            if 'cooldown_ms' in kwargs:
                self.cooldown = kwargs['cooldown_ms'] / 1000.0
                self.config['cooldown_ms'] = kwargs['cooldown_ms']
            if 'key_press_duration_ms' in kwargs:
                self.key_press_duration = kwargs['key_press_duration_ms'] / 1000.0
                self.config['key_press_duration_ms'] = kwargs['key_press_duration_ms']
        
        self.save_config()
    
    def capture_hp_bar(self, use_temp_mss=False):
        # MSS nesnesi thread-safe değil, her thread'de ayrı oluşturulmalı
        # use_temp_mss: GUI'den çağrıldığında geçici MSS kullan
        if use_temp_mss or self.sct is None:
            sct = mss.mss()
        else:
            sct = self.sct
        
        with self.lock:
            hp_bar = self.hp_bar.copy()
        
        monitor = {
            "top": hp_bar["y"],
            "left": hp_bar["x"],
            "width": hp_bar["width"],
            "height": hp_bar["height"]
        }
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img_array = np.array(img)
        
        # Debug için görüntüyü kaydet (sadece bot thread'inde)
        if not use_temp_mss and self.debug_image_callback:
            try:
                self.debug_image_callback(img_array.copy())
            except:
                pass
        
        return img_array
    
    def calculate_hp_percentage(self, hp_bar_image):
        height, width = hp_bar_image.shape[:2]
        
        if height == 0 or width == 0:
            return 0
        
        # Tüm satırların ortalamasını al (daha stabil)
        avg_line = np.mean(hp_bar_image, axis=0).astype(np.uint8)
        
        # RGB kanalları
        r = avg_line[:, 0]
        g = avg_line[:, 1]
        b = avg_line[:, 2]
        
        # Sol taraftaki ilk birkaç pikseli analiz et (can barının rengini bul)
        sample_width = min(20, width // 4)
        sample_r = r[:sample_width]
        sample_g = g[:sample_width]
        sample_b = b[:sample_width]
        
        # Can barının ortalama rengini hesapla
        hp_color_r = np.mean(sample_r)
        hp_color_g = np.mean(sample_g)
        hp_color_b = np.mean(sample_b)
        
        # Sağ taraftaki son birkaç pikseli analiz et (boş alanın rengini bul)
        empty_sample_r = r[-sample_width:]
        empty_sample_g = g[-sample_width:]
        empty_sample_b = b[-sample_width:]
        
        empty_color_r = np.mean(empty_sample_r)
        empty_color_g = np.mean(empty_sample_g)
        empty_color_b = np.mean(empty_sample_b)
        
        # Renk farkını hesapla
        color_diff = abs(hp_color_r - empty_color_r) + abs(hp_color_g - empty_color_g) + abs(hp_color_b - empty_color_b)
        
        # Eğer renk farkı çok küçükse, parlaklık farkını kullan
        if color_diff < 30:
            hp_brightness = (hp_color_r + hp_color_g + hp_color_b) / 3
            empty_brightness = (empty_color_r + empty_color_g + empty_color_b) / 3
            brightness_diff = abs(hp_brightness - empty_brightness)
            
            if brightness_diff > 20:
                # Parlaklık farkı ile tespit
                threshold = (hp_brightness + empty_brightness) / 2
                brightness = (r + g + b) / 3
                hp_mask = brightness > threshold
            else:
                # Çok küçük fark, varsayılan olarak tam dolu kabul et
                return 100.0
        else:
            # Renk farkı ile tespit
            # Her pikselin can barı rengine olan uzaklığını hesapla
            color_distance = np.sqrt(
                (r - hp_color_r) ** 2 + 
                (g - hp_color_g) ** 2 + 
                (b - hp_color_b) ** 2
            )
            
            empty_distance = np.sqrt(
                (r - empty_color_r) ** 2 + 
                (g - empty_color_g) ** 2 + 
                (b - empty_color_b) ** 2
            )
            
            # Eşik değeri: can barı rengine daha yakın olan pikseller
            hp_mask = color_distance < empty_distance
            
            # Eğer çok az eşleşme varsa, toleransı artır
            if np.sum(hp_mask) < width * 0.1:
                # Daha toleranslı eşik
                threshold_distance = np.max(color_distance[:sample_width]) * 1.5
                hp_mask = color_distance < threshold_distance
        
        # Soldan sağa tarayarak can barının bittiği yeri bul
        # Smoothing için: birkaç ardışık pikselin çoğunun boş olması gerekir
        hp_end = width
        
        # İlk 10 piksel her zaman can barı olarak kabul et (gürültü önleme)
        start_check = max(10, sample_width)
        
        for i in range(start_check, width):
            # Şu anki piksel ve sonraki birkaç pikseli kontrol et
            check_range = min(5, width - i)
            hp_count = np.sum(hp_mask[i:i+check_range])
            
            # Eğer çoğunluğu boşsa, can barı burada bitiyor
            if hp_count < (check_range * 0.3):
                hp_end = i
                break
        
        # Can yüzdesini hesapla
        hp_percentage = (hp_end / width) * 100
        
        return max(0, min(100, hp_percentage))
    
    def press_key(self):
        current_time = time.time()
        
        with self.lock:
            if current_time - self.last_potion_time < self.cooldown:
                return False
            key_to_press = self.key_to_press
            key_press_duration = self.key_press_duration
        
        try:
            if len(key_to_press) == 1:
                self.keyboard_controller.press(key_to_press)
                time.sleep(key_press_duration)  # Doğal tuş basma gecikmesi
                self.keyboard_controller.release(key_to_press)
            elif key_to_press.lower().startswith('f'):
                f_key_map = {
                    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
                    'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
                    'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12
                }
                key_obj = f_key_map.get(key_to_press.lower())
                if key_obj:
                    self.keyboard_controller.press(key_obj)
                    time.sleep(key_press_duration)  # Doğal tuş basma gecikmesi
                    self.keyboard_controller.release(key_obj)
            
            with self.lock:
                self.last_potion_time = current_time
                self.potion_count += 1
            
            if self.on_potion_used:
                self.on_potion_used(self.potion_count, key_to_press)
            
            return True
        except Exception as e:
            if self.on_potion_used:
                self.on_potion_used(-1, f"Hata: {e}")
            return False
    
    def _bot_loop(self):
        # MSS nesnesini bu thread'de oluştur (thread-safe için)
        self.sct = mss.mss()
        
        while self.running:
            try:
                hp_bar_image = self.capture_hp_bar()
                hp_percentage = self.calculate_hp_percentage(hp_bar_image)
                
                if self.on_hp_update:
                    self.on_hp_update(hp_percentage)
                
                with self.lock:
                    threshold = self.hp_threshold
                    check_interval = self.check_interval
                
                if hp_percentage <= threshold:
                    self.press_key()
                    time.sleep(self.cooldown)
                else:
                    time.sleep(check_interval)
                    
            except Exception as e:
                if self.on_hp_update:
                    self.on_hp_update(-1, error=str(e))
                time.sleep(1)
    
    def start(self):
        if not self.running:
            self.running = True
            self.bot_thread = threading.Thread(target=self._bot_loop, daemon=True)
            self.bot_thread.start()
            return True
        return False
    
    def stop(self):
        self.running = False
        if self.bot_thread:
            self.bot_thread.join(timeout=2.0)
    
    def get_stats(self):
        with self.lock:
            return {
                'potion_count': self.potion_count,
                'last_potion_time': self.last_potion_time,
                'running': self.running
            }

