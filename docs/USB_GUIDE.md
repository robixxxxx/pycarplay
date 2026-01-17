# PyCarPlay - USB Dongle Communication

## Dodane funkcje

### USB Dongle Driver (`dongle_driver.py`)

Pełna implementacja komunikacji z donglem CarPlay/AndroidAuto:

- **Obsługiwane urządzenia**: 
  - Vendor ID: 0x1314, Product ID: 0x1520
  - Vendor ID: 0x1314, Product ID: 0x1521

- **Funkcje**:
  - Automatyczne wykrywanie urządzenia USB
  - Inicjalizacja połączenia
  - Wysyłanie konfiguracji (rozdzielczość, FPS, DPI, etc.)
  - Heartbeat (co 2 sekundy)
  - Odczyt wiadomości w osobnym wątku
  - Obsługa błędów i automatyczne zamykanie przy awarii

### Integracja z GUI

- Status dongla wyświetlany w nagłówku (zielony/czerwony/żółty)
- Przycisk Connect/Disconnect
- Automatyczna obsługa wiadomości z dongla

## Instalacja wymagań

```bash
pip install -r requirements.txt
```

### macOS - wymagania dodatkowe

Na macOS może być potrzebne zainstalowanie libusb:

```bash
brew install libusb
```

### Linux - uprawnienia USB

Na Linuxie może być potrzebne dodanie reguł udev:

```bash
sudo nano /etc/udev/rules.d/99-carplay.rules
```

Dodaj:
```
SUBSYSTEM=="usb", ATTRS{idVendor}=="1314", ATTRS{idProduct}=="1520", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1314", ATTRS{idProduct}=="1521", MODE="0666"
```

Następnie:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Użycie

1. Podłącz dongle USB CarPlay/AndroidAuto
2. Uruchom aplikację: `python main.py`
3. Kliknij "Connect USB" aby połączyć się z donglem
4. Status połączenia będzie widoczny w nagłówku

## Konfiguracja

Możesz dostosować konfigurację w `main.py`:

```python
config = DongleConfig(
    width=1280,           # Rozdzielczość ekranu
    height=720,
    fps=30,               # Klatki na sekundę
    dpi=160,              # DPI ekranu
    box_name="pyCarPlay", # Nazwa urządzenia
    hand=HandDriveType.LHD,  # LHD lub RHD
    wifi_type="5ghz",     # "5ghz" lub "2.4ghz"
    mic_type="os"         # "os" lub "box"
)
```

## Architektura komunikacji

### Typy wiadomości

1. **SendNumber** - Wysyła wartość liczbową (DPI, tryb jazdy)
2. **SendBoolean** - Wysyła wartość boolean (tryb nocny, ładowanie)
3. **SendString** - Wysyła tekst (nazwa urządzenia)
4. **SendOpen** - Inicjalizacja z pełną konfiguracją
5. **SendBoxSettings** - Ustawienia urządzenia
6. **SendCommand** - Komendy (WiFi, mikrofon, audio)
7. **HeartBeat** - Utrzymanie połączenia

### Przepływ danych

```
[Python App] --USB--> [Dongle] --WiFi--> [iPhone/Android]
                  <--USB--         <--WiFi--
```

## Debugging

Driver loguje wszystkie operacje do konsoli:
- Inicjalizacja urządzenia
- Wysyłane wiadomości
- Otrzymane wiadomości
- Błędy komunikacji

## Następne kroki

- [ ] Dekodowanie video framów z dongla
- [ ] Wyświetlanie video w QML VideoOutput
- [ ] Obsługa audio
- [ ] Obsługa dotyku (touch events)
- [ ] Obsługa klawiatury/kontrolerów
