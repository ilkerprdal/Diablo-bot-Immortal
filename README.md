# Diablo Immortal Can İzleme Botu

Sol üstteki oyuncu can göstergesini izleyen ve belirlenen eşiğe ulaştığında otomatik olarak potion kullanan modern GUI tabanlı bot.

## Özellikler

- 🎨 Modern CustomTkinter GUI arayüzü
- ⚙️ Tüm ayarlar arayüzden yapılabilir
- 📊 Real-time can yüzdesi gösterimi
- 📝 Detaylı log sistemi
- 🔧 Thread-safe bot motoru
- 💾 Otomatik ayar kaydetme

## Kurulum

1. Python 3.8+ yüklü olmalı
2. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

## Kullanım

### GUI Modu (Önerilen)

```bash
python bot.py
```

veya doğrudan:

```bash
python gui.py
```

### GUI Özellikleri

**Sol Panel - Ayarlar:**
- Can barı konumu (X, Y, Width, Height)
- Can eşiği slider'ı
- Basılacak tuş seçimi
- Sağlıklı ve düşük can renk ayarları (RGB)
- Kontrol aralığı ve cooldown ayarları

**Sağ Panel - Durum:**
- Real-time can yüzdesi göstergesi
- Renk kodlu progress bar (yeşil → sarı → kırmızı)
- Bot durumu (Çalışıyor/Durduruldu)
- Potion kullanım istatistikleri
- Detaylı log penceresi

**Kontroller:**
- **Başlat/Durdur**: Botu başlatır veya durdurur
- **Ayarları Kaydet**: Değişiklikleri config.json'a kaydeder
- **Ayarları Yükle**: Config.json'dan ayarları yükler

## Yapılandırma

Ayarlar GUI üzerinden yapılabildiği gibi `config.json` dosyasını düzenleyerek de özelleştirebilirsiniz:

- **hp_bar**: Can barının ekrandaki konumu ve boyutu
- **hp_colors**: Can barı renk aralıkları (RGB)
- **hp_threshold**: Potion kullanılacak can yüzdesi
- **key_to_press**: Basılacak tuş
- **check_interval_ms**: Kontrol aralığı
- **cooldown_ms**: Potion cooldown süresi

## Can Barı Kalibrasyonu

1. Oyunu tam ekran modunda açın
2. Can barını görünür hale getirin
3. GUI'deki ayarlar panelinden koordinatları girin:
   - **X, Y**: Can barının sol üst köşe koordinatları
   - **Width, Height**: Can barının genişlik ve yüksekliği
4. Renk aralıklarını ayarlayın (RGB değerleri)
5. "Ayarları Kaydet" butonuna basın

## Dosya Yapısı

- `bot.py` - Ana giriş noktası (GUI başlatır)
- `gui.py` - CustomTkinter GUI uygulaması
- `bot_engine.py` - Thread-safe bot motoru
- `config.json` - Yapılandırma dosyası

## Notlar

- Bot yalnızca eğitim amaçlıdır
- Oyun kurallarına uygun kullanın
- Test ortamında kullanmayı öneririz
- İlk kullanımda can barı koordinatlarını ve renkleri kalibre etmeniz gerekebilir

