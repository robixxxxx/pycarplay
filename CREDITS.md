# Credits

## Original Project

Based on **[react-carplay](https://github.com/rhysmorgan134/react-carplay)** by **Rhys Morgan**.

## Differences from Original

| Aspect | react-carplay | PyCarPlay-Qt |
|--------|---------------|--------------|
| **Framework** | React/Electron | PySide6/Qt |
| **Language** | JavaScript/TypeScript | Python |
| **UI** | React components | QML components |
| **Configuration** | Limited | Extensive dataclass-based |
| **Protocol** | Opinionated | Agnostic (developer's choice) |
| **Target** | Web-based UI | Embedded/automotive |
| **Hardware** | Browser-based | Direct GPIO/serial/CAN |

## Key Adaptations

### 1. Configuration System
- Complete control over video (resolution, DPI, FPS)
- Audio settings (sample rate, channels, buffer)
- UI customization
- Dongle connection parameters

### 2. Protocol Independence
Widget provides clean API without vehicle protocol assumptions:
- No built-in CAN/LIN/MOST handlers
- No vehicle-specific message definitions
- Developer implements their own communication layer

Example integration:
```python
carplay = CarPlayWidget()

# Developer chooses communication method:
def on_can_message(msg_id, data):    # CAN bus
    if msg_id == 0x123:
        carplay.send_home()

def on_gpio_interrupt(pin):          # GPIO
    carplay.send_play_pause()

def on_serial_command(cmd):          # Serial
    carplay.send_next_track()
```

### 3. Qt Integration
- Native PySide6/PyQt6 support
- Qt signals/slots for events
- QML components
- Thread-safe operation

## License

MIT License (compatible with react-carplay)

## Thanks

- **Rhys Morgan** - For react-carplay
- **Qt/PySide6 team** - For Python bindings

