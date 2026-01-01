import customtkinter as ctk
import threading
import json
from datetime import datetime
import numpy as np
from bot_engine import DiabloImmortalBotEngine
from region_selector import RegionSelector
from map_region_selector import MapRegionSelector
from farming_engine import FarmingEngine

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class DiabloImmortalBotGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Diablo Immortal HP Bot")
        self.root.geometry("900x700")
        
        self.bot_engine = DiabloImmortalBotEngine(
            on_hp_update=self.on_hp_update,
            on_potion_used=self.on_potion_used,
            on_debug_image=self.on_debug_image
        )
        
        self.farming_engine = FarmingEngine(
            on_position_update=self.on_farming_position_update,
            on_boundary_warning=self.on_farming_boundary_warning
        )
        
        self.current_hp = 100.0
        self.last_debug_image = None
        self.setup_ui()
        self.load_config_to_ui()
    
    def setup_ui(self):
        # Ana container
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab View
        self.tabview = ctk.CTkTabview(main_container)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # HP Bot Tab
        self.hp_bot_tab = self.tabview.add("HP Bot")
        
        # Farming Modu Tab
        self.farming_tab = self.tabview.add("Farming Modu")
        
        # Sol panel - HP Bot Ayarları
        left_panel = ctk.CTkFrame(self.hp_bot_tab)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        settings_label = ctk.CTkLabel(left_panel, text="Ayarlar", font=ctk.CTkFont(size=20, weight="bold"))
        settings_label.pack(pady=(10, 20))
        
        # Can Barı Konumu
        hp_bar_frame = ctk.CTkFrame(left_panel)
        hp_bar_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(hp_bar_frame, text="Can Barı Konumu", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 10))
        
        pos_row1 = ctk.CTkFrame(hp_bar_frame)
        pos_row1.pack(fill="x", pady=2)
        ctk.CTkLabel(pos_row1, text="X:", width=30).pack(side="left", padx=5)
        self.x_entry = ctk.CTkEntry(pos_row1, width=80)
        self.x_entry.pack(side="left", padx=5)
        ctk.CTkLabel(pos_row1, text="Y:", width=30).pack(side="left", padx=5)
        self.y_entry = ctk.CTkEntry(pos_row1, width=80)
        self.y_entry.pack(side="left", padx=5)
        
        pos_row2 = ctk.CTkFrame(hp_bar_frame)
        pos_row2.pack(fill="x", pady=2)
        ctk.CTkLabel(pos_row2, text="W:", width=30).pack(side="left", padx=5)
        self.w_entry = ctk.CTkEntry(pos_row2, width=80)
        self.w_entry.pack(side="left", padx=5)
        ctk.CTkLabel(pos_row2, text="H:", width=30).pack(side="left", padx=5)
        self.h_entry = ctk.CTkEntry(pos_row2, width=80)
        self.h_entry.pack(side="left", padx=5)
        
        # Can Barını Seç butonu
        button_row = ctk.CTkFrame(hp_bar_frame)
        button_row.pack(pady=10)
        
        select_button = ctk.CTkButton(
            button_row, 
            text="Can Barını Seç", 
            command=self.select_region,
            width=150,
            height=30
        )
        select_button.pack(side="left", padx=5)
        
        auto_color_button = ctk.CTkButton(
            button_row, 
            text="Renkleri Otomatik Algıla", 
            command=self.auto_detect_colors,
            width=180,
            height=30
        )
        auto_color_button.pack(side="left", padx=5)
        
        # Can Eşiği
        threshold_frame = ctk.CTkFrame(left_panel)
        threshold_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(threshold_frame, text="Can Eşiği (%)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 5))
        
        threshold_container = ctk.CTkFrame(threshold_frame)
        threshold_container.pack(fill="x", pady=5)
        
        self.threshold_slider = ctk.CTkSlider(threshold_container, from_=1, to=99, command=self.on_threshold_change)
        self.threshold_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.threshold_label = ctk.CTkLabel(threshold_container, text="30%", width=50)
        self.threshold_label.pack(side="right", padx=5)
        
        # Tuş Seçimi
        key_frame = ctk.CTkFrame(left_panel)
        key_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(key_frame, text="Basılacak Tuş", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 5))
        
        keys = ["q", "e", "r", "f", "1", "2", "3", "4", "f1", "f2", "f3", "f4"]
        self.key_var = ctk.StringVar(value="q")
        self.key_dropdown = ctk.CTkComboBox(key_frame, values=keys, variable=self.key_var, width=200)
        self.key_dropdown.pack(pady=5)
        
        # Renk Ayarları
        colors_frame = ctk.CTkFrame(left_panel)
        colors_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(colors_frame, text="Sağlıklı Can Rengi (RGB)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 5))
        
        healthy_row1 = ctk.CTkFrame(colors_frame)
        healthy_row1.pack(fill="x", pady=2)
        ctk.CTkLabel(healthy_row1, text="Min:", width=40).pack(side="left", padx=5)
        self.h_healthy_min_r = ctk.CTkEntry(healthy_row1, width=50)
        self.h_healthy_min_r.pack(side="left", padx=2)
        self.h_healthy_min_g = ctk.CTkEntry(healthy_row1, width=50)
        self.h_healthy_min_g.pack(side="left", padx=2)
        self.h_healthy_min_b = ctk.CTkEntry(healthy_row1, width=50)
        self.h_healthy_min_b.pack(side="left", padx=2)
        
        healthy_row2 = ctk.CTkFrame(colors_frame)
        healthy_row2.pack(fill="x", pady=2)
        ctk.CTkLabel(healthy_row2, text="Max:", width=40).pack(side="left", padx=5)
        self.h_healthy_max_r = ctk.CTkEntry(healthy_row2, width=50)
        self.h_healthy_max_r.pack(side="left", padx=2)
        self.h_healthy_max_g = ctk.CTkEntry(healthy_row2, width=50)
        self.h_healthy_max_g.pack(side="left", padx=2)
        self.h_healthy_max_b = ctk.CTkEntry(healthy_row2, width=50)
        self.h_healthy_max_b.pack(side="left", padx=2)
        
        ctk.CTkLabel(colors_frame, text="Düşük Can Rengi (RGB)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 5))
        
        low_row1 = ctk.CTkFrame(colors_frame)
        low_row1.pack(fill="x", pady=2)
        ctk.CTkLabel(low_row1, text="Min:", width=40).pack(side="left", padx=5)
        self.h_low_min_r = ctk.CTkEntry(low_row1, width=50)
        self.h_low_min_r.pack(side="left", padx=2)
        self.h_low_min_g = ctk.CTkEntry(low_row1, width=50)
        self.h_low_min_g.pack(side="left", padx=2)
        self.h_low_min_b = ctk.CTkEntry(low_row1, width=50)
        self.h_low_min_b.pack(side="left", padx=2)
        
        low_row2 = ctk.CTkFrame(colors_frame)
        low_row2.pack(fill="x", pady=2)
        ctk.CTkLabel(low_row2, text="Max:", width=40).pack(side="left", padx=5)
        self.h_low_max_r = ctk.CTkEntry(low_row2, width=50)
        self.h_low_max_r.pack(side="left", padx=2)
        self.h_low_max_g = ctk.CTkEntry(low_row2, width=50)
        self.h_low_max_g.pack(side="left", padx=2)
        self.h_low_max_b = ctk.CTkEntry(low_row2, width=50)
        self.h_low_max_b.pack(side="left", padx=2)
        
        # Diğer Ayarlar
        other_frame = ctk.CTkFrame(left_panel)
        other_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(other_frame, text="Kontrol Aralığı (ms)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 5))
        self.interval_entry = ctk.CTkEntry(other_frame, width=150)
        self.interval_entry.pack(pady=2)
        
        ctk.CTkLabel(other_frame, text="Cooldown (ms)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 5))
        self.cooldown_entry = ctk.CTkEntry(other_frame, width=150)
        self.cooldown_entry.pack(pady=2)
        
        ctk.CTkLabel(other_frame, text="Tuş Basma Süresi (ms)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 5))
        self.key_press_duration_entry = ctk.CTkEntry(other_frame, width=150)
        self.key_press_duration_entry.pack(pady=2)
        ctk.CTkLabel(other_frame, text="(Tuş basılı kalma süresi, önerilen: 60ms)", font=ctk.CTkFont(size=10)).pack(anchor="w", pady=(0, 5))
        
        # Sağ panel - Durum (HP Bot için)
        right_panel = ctk.CTkFrame(self.hp_bot_tab)
        right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        status_label = ctk.CTkLabel(right_panel, text="Durum", font=ctk.CTkFont(size=20, weight="bold"))
        status_label.pack(pady=(10, 20))
        
        # Can Göstergesi
        hp_display_frame = ctk.CTkFrame(right_panel)
        hp_display_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(hp_display_frame, text="Can Yüzdesi", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        self.hp_percentage_label = ctk.CTkLabel(hp_display_frame, text="100.0%", font=ctk.CTkFont(size=32, weight="bold"))
        self.hp_percentage_label.pack(pady=5)
        
        self.hp_progress = ctk.CTkProgressBar(hp_display_frame, width=300, height=30)
        self.hp_progress.pack(pady=10, padx=20, fill="x")
        self.hp_progress.set(1.0)
        
        # Bot Durumu
        bot_status_frame = ctk.CTkFrame(right_panel)
        bot_status_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(bot_status_frame, text="Bot Durumu", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        self.bot_status_label = ctk.CTkLabel(bot_status_frame, text="Durduruldu", font=ctk.CTkFont(size=16))
        self.bot_status_label.pack(pady=5)
        
        self.stats_label = ctk.CTkLabel(bot_status_frame, text="Potion Sayısı: 0", font=ctk.CTkFont(size=12))
        self.stats_label.pack(pady=5)
        
        # Log Alanı
        log_frame = ctk.CTkFrame(right_panel)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(log_frame, text="Log", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        
        self.log_textbox = ctk.CTkTextbox(log_frame, height=200)
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Alt Panel - Kontroller (HP Bot için)
        control_panel = ctk.CTkFrame(self.hp_bot_tab)
        control_panel.pack(fill="x", pady=(10, 0))
        
        self.start_button = ctk.CTkButton(control_panel, text="Başlat", command=self.toggle_bot, width=120, height=40)
        self.start_button.pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(control_panel, text="Ayarları Kaydet", command=self.save_settings, width=120, height=40).pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(control_panel, text="Ayarları Yükle", command=self.load_config_to_ui, width=120, height=40).pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(control_panel, text="Can Barı Görüntüsü Kaydet", command=self.save_debug_image, width=150, height=40).pack(side="left", padx=10, pady=10)
        
        # Farming Modu UI
        self.setup_farming_ui()
        
        self.update_stats_loop()
    
    def on_threshold_change(self, value):
        self.threshold_label.configure(text=f"{int(value)}%")
    
    def load_config_to_ui(self):
        config = self.bot_engine.config
        
        # Can barı konumu
        hp_bar = config['hp_bar']
        self.x_entry.delete(0, "end")
        self.x_entry.insert(0, str(hp_bar['x']))
        self.y_entry.delete(0, "end")
        self.y_entry.insert(0, str(hp_bar['y']))
        self.w_entry.delete(0, "end")
        self.w_entry.insert(0, str(hp_bar['width']))
        self.h_entry.delete(0, "end")
        self.h_entry.insert(0, str(hp_bar['height']))
        
        # Can eşiği
        threshold = config['hp_threshold']
        self.threshold_slider.set(threshold)
        self.threshold_label.configure(text=f"{threshold}%")
        
        # Tuş
        self.key_var.set(config['key_to_press'])
        
        # Renkler
        colors = config['hp_colors']
        self.h_healthy_min_r.delete(0, "end")
        self.h_healthy_min_r.insert(0, str(colors['healthy_min'][0]))
        self.h_healthy_min_g.delete(0, "end")
        self.h_healthy_min_g.insert(0, str(colors['healthy_min'][1]))
        self.h_healthy_min_b.delete(0, "end")
        self.h_healthy_min_b.insert(0, str(colors['healthy_min'][2]))
        
        self.h_healthy_max_r.delete(0, "end")
        self.h_healthy_max_r.insert(0, str(colors['healthy_max'][0]))
        self.h_healthy_max_g.delete(0, "end")
        self.h_healthy_max_g.insert(0, str(colors['healthy_max'][1]))
        self.h_healthy_max_b.delete(0, "end")
        self.h_healthy_max_b.insert(0, str(colors['healthy_max'][2]))
        
        self.h_low_min_r.delete(0, "end")
        self.h_low_min_r.insert(0, str(colors['low_hp_min'][0]))
        self.h_low_min_g.delete(0, "end")
        self.h_low_min_g.insert(0, str(colors['low_hp_min'][1]))
        self.h_low_min_b.delete(0, "end")
        self.h_low_min_b.insert(0, str(colors['low_hp_min'][2]))
        
        self.h_low_max_r.delete(0, "end")
        self.h_low_max_r.insert(0, str(colors['low_hp_max'][0]))
        self.h_low_max_g.delete(0, "end")
        self.h_low_max_g.insert(0, str(colors['low_hp_max'][1]))
        self.h_low_max_b.delete(0, "end")
        self.h_low_max_b.insert(0, str(colors['low_hp_max'][2]))
        
        # Diğer ayarlar
        self.interval_entry.delete(0, "end")
        self.interval_entry.insert(0, str(config['check_interval_ms']))
        self.cooldown_entry.delete(0, "end")
        self.cooldown_entry.insert(0, str(config['cooldown_ms']))
        self.key_press_duration_entry.delete(0, "end")
        self.key_press_duration_entry.insert(0, str(config.get('key_press_duration_ms', 60)))
    
    def save_settings(self):
        try:
            hp_bar = {
                'x': int(self.x_entry.get()),
                'y': int(self.y_entry.get()),
                'width': int(self.w_entry.get()),
                'height': int(self.h_entry.get())
            }
            
            hp_colors = {
                'healthy_min': [
                    int(self.h_healthy_min_r.get()),
                    int(self.h_healthy_min_g.get()),
                    int(self.h_healthy_min_b.get())
                ],
                'healthy_max': [
                    int(self.h_healthy_max_r.get()),
                    int(self.h_healthy_max_g.get()),
                    int(self.h_healthy_max_b.get())
                ],
                'low_hp_min': [
                    int(self.h_low_min_r.get()),
                    int(self.h_low_min_g.get()),
                    int(self.h_low_min_b.get())
                ],
                'low_hp_max': [
                    int(self.h_low_max_r.get()),
                    int(self.h_low_max_g.get()),
                    int(self.h_low_max_b.get())
                ]
            }
            
            self.bot_engine.update_config(
                hp_bar=hp_bar,
                hp_colors=hp_colors,
                hp_threshold=int(self.threshold_slider.get()),
                key_to_press=self.key_var.get(),
                check_interval_ms=int(self.interval_entry.get()),
                cooldown_ms=int(self.cooldown_entry.get()),
                key_press_duration_ms=int(self.key_press_duration_entry.get())
            )
            
            self.add_log("Ayarlar kaydedildi!")
        except ValueError as e:
            self.add_log(f"Hata: Geçersiz değer - {e}")
        except Exception as e:
            self.add_log(f"Hata: {e}")
    
    def toggle_bot(self):
        if self.bot_engine.running:
            self.bot_engine.stop()
            self.start_button.configure(text="Başlat")
            self.bot_status_label.configure(text="Durduruldu", text_color="gray")
            self.add_log("Bot durduruldu")
        else:
            self.save_settings()
            if self.bot_engine.start():
                self.start_button.configure(text="Durdur")
                self.bot_status_label.configure(text="Çalışıyor", text_color="green")
                self.add_log("Bot başlatıldı")
            else:
                self.add_log("Bot başlatılamadı")
    
    def on_hp_update(self, hp_percentage, error=None):
        if error:
            self.add_log(f"Hata: {error}")
            return
        
        if hp_percentage < 0:
            return
        
        self.current_hp = hp_percentage
        hp_normalized = hp_percentage / 100.0
        
        # UI thread'de güncelle (lambda closure için değerleri kopyala)
        def update_ui():
            self.update_hp_display(hp_percentage, hp_normalized)
        self.root.after(0, update_ui)
    
    def update_hp_display(self, hp_percentage, hp_normalized):
        self.hp_percentage_label.configure(text=f"{hp_percentage:.1f}%")
        self.hp_progress.set(hp_normalized)
        
        # Renk güncelle (yeşil -> kırmızı)
        if hp_percentage > 50:
            color = "#00ff00"
        elif hp_percentage > 25:
            color = "#ffff00"
        else:
            color = "#ff0000"
        
        self.hp_percentage_label.configure(text_color=color)
    
    def on_potion_used(self, count, key_or_error):
        if count == -1:
            self.add_log(f"Potion hatası: {key_or_error}")
        else:
            self.add_log(f"Potion kullanıldı ({key_or_error}) - Toplam: {count}")
            def update_stats():
                self.stats_label.configure(text=f"Potion Sayısı: {count}")
            self.root.after(0, update_stats)
    
    def update_stats_loop(self):
        if self.bot_engine.running:
            stats = self.bot_engine.get_stats()
            # Stats güncellenebilir
        self.root.after(1000, self.update_stats_loop)
    
    def select_region(self):
        """Can barı bölgesini seçmek için region selector'ı aç"""
        def show_gui():
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        
        def on_region_selected(x, y, width, height):
            self.x_entry.delete(0, "end")
            self.x_entry.insert(0, str(x))
            self.y_entry.delete(0, "end")
            self.y_entry.insert(0, str(y))
            self.w_entry.delete(0, "end")
            self.w_entry.insert(0, str(width))
            self.h_entry.delete(0, "end")
            self.h_entry.insert(0, str(height))
            self.add_log(f"Can barı bölgesi seçildi: X={x}, Y={y}, W={width}, H={height}")
            show_gui()
        
        def on_cancel():
            self.add_log("Bölge seçimi iptal edildi")
            show_gui()
        
        # GUI'yi gizle
        self.root.withdraw()
        
        # Region selector'ı başlat
        try:
            # CustomTkinter root'u zaten tkinter root'u, parent olarak geç
            import tkinter as tk
            # CustomTkinter CTk objesi direkt tkinter root'u
            tk_root = self.root._w  # Internal tkinter widget id
            # Veya direkt root'u parent olarak kullanabiliriz
            selector = RegionSelector(on_region_selected, on_cancel, None)
        except Exception as e:
            self.add_log(f"Bölge seçici hatası: {e}")
            import traceback
            self.add_log(f"Detay: {traceback.format_exc()}")
            show_gui()
    
    def auto_detect_colors(self):
        """Can barı görüntüsünden renkleri otomatik algıla"""
        try:
            # Can barı görüntüsünü al (GUI thread'inden çağrıldığı için use_temp_mss=True)
            hp_bar_image = self.bot_engine.capture_hp_bar(use_temp_mss=True)
            
            if hp_bar_image is None or hp_bar_image.size == 0:
                self.add_log("Can barı görüntüsü alınamadı. Koordinatları kontrol edin.")
                return
            
            height, width = hp_bar_image.shape[:2]
            
            # Sol taraftaki ilk %20'yi analiz et (can barı rengi)
            sample_width = max(5, width // 5)
            hp_region = hp_bar_image[:, :sample_width]
            
            # Sağ taraftaki son %20'yi analiz et (boş alan)
            empty_region = hp_bar_image[:, -sample_width:]
            
            # Ortalama renkleri hesapla
            hp_color = np.mean(hp_region, axis=(0, 1)).astype(int)
            empty_color = np.mean(empty_region, axis=(0, 1)).astype(int)
            
            # Sağlıklı can için (sol taraf)
            self.h_healthy_min_r.delete(0, "end")
            self.h_healthy_min_r.insert(0, str(max(0, hp_color[0] - 30)))
            self.h_healthy_min_g.delete(0, "end")
            self.h_healthy_min_g.insert(0, str(max(0, hp_color[1] - 30)))
            self.h_healthy_min_b.delete(0, "end")
            self.h_healthy_min_b.insert(0, str(max(0, hp_color[2] - 30)))
            
            self.h_healthy_max_r.delete(0, "end")
            self.h_healthy_max_r.insert(0, str(min(255, hp_color[0] + 30)))
            self.h_healthy_max_g.delete(0, "end")
            self.h_healthy_max_g.insert(0, str(min(255, hp_color[1] + 30)))
            self.h_healthy_max_b.delete(0, "end")
            self.h_healthy_max_b.insert(0, str(min(255, hp_color[2] + 30)))
            
            # Düşük can için (sağlıklıya benzer ama biraz daha koyu)
            low_color = hp_color * 0.7  # %30 daha koyu
            
            self.h_low_min_r.delete(0, "end")
            self.h_low_min_r.insert(0, str(max(0, int(low_color[0] - 30))))
            self.h_low_min_g.delete(0, "end")
            self.h_low_min_g.insert(0, str(max(0, int(low_color[1] - 30))))
            self.h_low_min_b.delete(0, "end")
            self.h_low_min_b.insert(0, str(max(0, int(low_color[2] - 30))))
            
            self.h_low_max_r.delete(0, "end")
            self.h_low_max_r.insert(0, str(min(255, int(low_color[0] + 30))))
            self.h_low_max_g.delete(0, "end")
            self.h_low_max_g.insert(0, str(min(255, int(low_color[1] + 30))))
            self.h_low_max_b.delete(0, "end")
            self.h_low_max_b.insert(0, str(min(255, int(low_color[2] + 30))))
            
            self.add_log(f"Renkler otomatik algılandı! Can rengi: RGB({hp_color[0]}, {hp_color[1]}, {hp_color[2]})")
            self.add_log("Ayarları kaydetmeyi unutmayın!")
            
        except Exception as e:
            self.add_log(f"Renk algılama hatası: {e}")
            import traceback
            self.add_log(f"Detay: {traceback.format_exc()}")
    
    def on_debug_image(self, image_array):
        """Can barı görüntüsünü kaydet (debug için)"""
        self.last_debug_image = image_array
    
    def save_debug_image(self):
        """Can barı görüntüsünü dosyaya kaydet"""
        if self.last_debug_image is None:
            self.add_log("Henüz görüntü yakalanmadı. Botu başlatın veya bir süre bekleyin.")
            return
        
        try:
            from PIL import Image
            img = Image.fromarray(self.last_debug_image)
            filename = f"hp_bar_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            img.save(filename)
            self.add_log(f"Can barı görüntüsü kaydedildi: {filename}")
        except Exception as e:
            self.add_log(f"Görüntü kaydetme hatası: {e}")
    
    def setup_farming_ui(self):
        """Farming Modu sekmesi UI"""
        # Sol panel - Farming Ayarları
        farming_left_panel = ctk.CTkFrame(self.farming_tab)
        farming_left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        farming_label = ctk.CTkLabel(farming_left_panel, text="Farming Ayarları", font=ctk.CTkFont(size=20, weight="bold"))
        farming_label.pack(pady=(10, 20))
        
        # Mini Harita Bölgesi
        minimap_frame = ctk.CTkFrame(farming_left_panel)
        minimap_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(minimap_frame, text="Mini Harita Bölgesi", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 10))
        
        minimap_pos_frame = ctk.CTkFrame(minimap_frame)
        minimap_pos_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(minimap_pos_frame, text="X:", width=30).pack(side="left", padx=5)
        self.minimap_x_entry = ctk.CTkEntry(minimap_pos_frame, width=80)
        self.minimap_x_entry.pack(side="left", padx=5)
        ctk.CTkLabel(minimap_pos_frame, text="Y:", width=30).pack(side="left", padx=5)
        self.minimap_y_entry = ctk.CTkEntry(minimap_pos_frame, width=80)
        self.minimap_y_entry.pack(side="left", padx=5)
        
        minimap_size_frame = ctk.CTkFrame(minimap_frame)
        minimap_size_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(minimap_size_frame, text="W:", width=30).pack(side="left", padx=5)
        self.minimap_w_entry = ctk.CTkEntry(minimap_size_frame, width=80)
        self.minimap_w_entry.pack(side="left", padx=5)
        ctk.CTkLabel(minimap_size_frame, text="H:", width=30).pack(side="left", padx=5)
        self.minimap_h_entry = ctk.CTkEntry(minimap_size_frame, width=80)
        self.minimap_h_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(
            minimap_frame,
            text="Mini Harita Bölgesini Seç",
            command=self.select_minimap_region,
            width=200,
            height=30
        ).pack(pady=10)
        
        # Daire Parametreleri
        circle_frame = ctk.CTkFrame(farming_left_panel)
        circle_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(circle_frame, text="Daire Parametreleri", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5, 10))
        
        circle_center_frame = ctk.CTkFrame(circle_frame)
        circle_center_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(circle_center_frame, text="Merkez X:", width=60).pack(side="left", padx=5)
        self.circle_center_x_entry = ctk.CTkEntry(circle_center_frame, width=80)
        self.circle_center_x_entry.pack(side="left", padx=5)
        ctk.CTkLabel(circle_center_frame, text="Y:", width=30).pack(side="left", padx=5)
        self.circle_center_y_entry = ctk.CTkEntry(circle_center_frame, width=80)
        self.circle_center_y_entry.pack(side="left", padx=5)
        
        circle_radius_frame = ctk.CTkFrame(circle_frame)
        circle_radius_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(circle_radius_frame, text="Yarıçap:", width=60).pack(side="left", padx=5)
        self.circle_radius_entry = ctk.CTkEntry(circle_radius_frame, width=150)
        self.circle_radius_entry.pack(side="left", padx=5)
        
        # Sağ panel - Farming Durumu
        farming_right_panel = ctk.CTkFrame(self.farming_tab)
        farming_right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        farming_status_label = ctk.CTkLabel(farming_right_panel, text="Farming Durumu", font=ctk.CTkFont(size=20, weight="bold"))
        farming_status_label.pack(pady=(10, 20))
        
        # Pozisyon Bilgisi
        position_frame = ctk.CTkFrame(farming_right_panel)
        position_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(position_frame, text="Karakter Pozisyonu", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        self.farming_position_label = ctk.CTkLabel(position_frame, text="X: -, Y: -", font=ctk.CTkFont(size=14))
        self.farming_position_label.pack(pady=5)
        
        # Daire İçinde
        circle_status_frame = ctk.CTkFrame(farming_right_panel)
        circle_status_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(circle_status_frame, text="Daire İçinde", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
        self.farming_status_label = ctk.CTkLabel(circle_status_frame, text="Bilinmiyor", font=ctk.CTkFont(size=14))
        self.farming_status_label.pack(pady=5)
        
        # Farming Kontrolleri
        farming_control_panel = ctk.CTkFrame(self.farming_tab)
        farming_control_panel.pack(fill="x", pady=(10, 0))
        
        self.farming_start_button = ctk.CTkButton(
            farming_control_panel,
            text="Farming Başlat",
            command=self.toggle_farming,
            width=150,
            height=40
        )
        self.farming_start_button.pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(
            farming_control_panel,
            text="Ayarları Kaydet",
            command=self.save_farming_settings,
            width=120,
            height=40
        ).pack(side="left", padx=10, pady=10)
    
    def select_minimap_region(self):
        """Mini harita bölgesini seç"""
        def on_region_selected(region, circle_center, radius):
            def update_ui():
                try:
                    self.minimap_x_entry.delete(0, "end")
                    self.minimap_x_entry.insert(0, str(region['x']))
                    self.minimap_y_entry.delete(0, "end")
                    self.minimap_y_entry.insert(0, str(region['y']))
                    self.minimap_w_entry.delete(0, "end")
                    self.minimap_w_entry.insert(0, str(region['width']))
                    self.minimap_h_entry.delete(0, "end")
                    self.minimap_h_entry.insert(0, str(region['height']))
                    
                    self.circle_center_x_entry.delete(0, "end")
                    self.circle_center_x_entry.insert(0, str(circle_center['x']))
                    self.circle_center_y_entry.delete(0, "end")
                    self.circle_center_y_entry.insert(0, str(circle_center['y']))
                    
                    self.circle_radius_entry.delete(0, "end")
                    self.circle_radius_entry.insert(0, str(radius))
                    
                    self.add_log(f"Mini harita bölgesi ve daire seçildi!")
                    show_gui()
                except Exception as e:
                    self.add_log(f"Bölge seçimi callback hatası: {e}")
                    show_gui()
            
            self.root.after(0, update_ui)
        
        def show_gui():
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
            except:
                pass
        
        def on_cancel():
            self.add_log("Mini harita seçimi iptal edildi")
            show_gui()
        
        try:
            self.root.withdraw()
            selector = MapRegionSelector(on_region_selected, on_cancel, None)
        except Exception as e:
            self.add_log(f"Mini harita seçici hatası: {e}")
            import traceback
            self.add_log(f"Detay: {traceback.format_exc()}")
            show_gui()
    
    def save_farming_settings(self):
        """Farming ayarlarını kaydet"""
        try:
            minimap_region = {
                "x": int(self.minimap_x_entry.get()),
                "y": int(self.minimap_y_entry.get()),
                "width": int(self.minimap_w_entry.get()),
                "height": int(self.minimap_h_entry.get())
            }
            
            circle_center = {
                "x": int(self.circle_center_x_entry.get()),
                "y": int(self.circle_center_y_entry.get())
            }
            
            circle_radius = int(self.circle_radius_entry.get())
            
            self.farming_engine.set_minimap_region(**minimap_region)
            self.farming_engine.set_circle(circle_center["x"], circle_center["y"], circle_radius)
            
            self.add_log("Farming ayarları kaydedildi!")
        except ValueError as e:
            self.add_log(f"Hata: Geçersiz değer - {e}")
        except Exception as e:
            self.add_log(f"Hata: {e}")
    
    def toggle_farming(self):
        """Farming modunu başlat/durdur"""
        if self.farming_engine.running:
            self.farming_engine.stop()
            self.farming_start_button.configure(text="Farming Başlat")
            self.farming_status_label.configure(text="Durduruldu", text_color="gray")
            self.add_log("Farming modu durduruldu")
        else:
            self.save_farming_settings()
            success, message = self.farming_engine.start()
            if success:
                self.farming_start_button.configure(text="Farming Durdur")
                self.farming_status_label.configure(text="Çalışıyor", text_color="green")
                self.add_log(message)
            else:
                self.add_log(f"Farming başlatılamadı: {message}")
    
    def on_farming_position_update(self, position, circle_center, circle_radius):
        """Farming pozisyon güncellemesi"""
        if position:
            def update_ui():
                self.farming_position_label.configure(text=f"X: {position['x']}, Y: {position['y']}")
                import math
                dx = position['x'] - circle_center['x']
                dy = position['y'] - circle_center['y']
                distance = math.sqrt(dx**2 + dy**2)
                is_inside = distance <= circle_radius
                if is_inside:
                    self.farming_status_label.configure(text=f"Daire içinde (Mesafe: {distance:.1f}/{circle_radius})", text_color="green")
                else:
                    self.farming_status_label.configure(text=f"Daire dışında (Mesafe: {distance:.1f}/{circle_radius})", text_color="red")
            self.root.after(0, update_ui)
    
    def on_farming_boundary_warning(self, *args):
        """Farming sınır uyarısı"""
        if len(args) > 0:
            message = str(args[0]) if isinstance(args[0], str) else f"Uyarı: {args}"
            self.add_log(f"Farming: {message}")
    
    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.root.after(0, lambda: self.log_textbox.insert("end", log_message))
        self.root.after(0, lambda: self.log_textbox.see("end"))
    
    def run(self):
        self.root.mainloop()
        self.bot_engine.stop()
        self.farming_engine.stop()

if __name__ == "__main__":
    app = DiabloImmortalBotGUI()
    app.run()

