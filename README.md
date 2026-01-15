# iPixel LED Panel Controller

A desktop application to control iPixel Color LED matrix displays (like BGLight, B.K. Light LED Pixel Board) directly from your Windows PC via Bluetooth.

![iPixel Controller](screenshot.png)

## Features

- 🔍 **Auto-scan** for iPixel devices via Bluetooth
- 📝 **Send text** with customizable font size, text color, and background color
- 🖼️ **Display images** (PNG, JPG, GIF, BMP)
- 🕐 **Clock mode** with 9 different styles
- 💡 **Brightness control** (1-100%)
- ⚡ **Power control** (ON/OFF)
- 🎨 **Color picker** for text and background
- 🖥️ **Easy-to-use GUI** built with Tkinter

## Requirements

- Windows 10/11 (with Bluetooth LE support)
- Python 3.8 or higher
- Bluetooth adapter (built-in or USB dongle)
- iPixel Color LED panel (BGLight, B.K. Light, etc.)

## Installation

### Method 1: Using Python (Recommended)

1. **Install Python** (if not already installed):
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"

2. **Download this application**:
   - Download all files to a folder (e.g., `C:\iPixel`)

3. **Install dependencies**:
   ```bash
   cd C:\iPixel
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python ipixel_controller.py
   ```

### Method 2: Create a Standalone Executable (Optional)

To create a standalone .exe file that doesn't require Python:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Create the executable:
   ```bash
   pyinstaller --onefile --windowed --name "iPixel Controller" ipixel_controller.py
   ```

3. Find the executable in the `dist` folder

## Usage

### 1. Connect to Your Device

1. Turn on your iPixel LED panel
2. Click **"Scan"** to search for nearby Bluetooth devices
3. Select your device from the dropdown (usually named "LED_BLE_...")
4. Click **"Connect"**
5. Wait for "Connected" status (green)

### 2. Send Text

1. Go to the **"Text"** tab
2. Enter your text in the text box
3. Choose text color (default: white)
4. Choose background color (default: black)
5. Adjust font size (6-32)
6. Click **"Send Text"**

**Tips:**
- Keep text short for better readability on small displays
- Smaller font sizes work better for longer text
- High contrast (white on black) is most readable

### 3. Display Images

1. Go to the **"Image"** tab
2. Click **"Load Image"** and select an image file
3. Preview appears in the window
4. Click **"Send Image"**

**Supported formats:** PNG, JPG, JPEG, GIF, BMP

**Tips:**
- Images are automatically resized to fit your panel
- For best results, use images with your panel's exact resolution
- Common panel sizes: 64x64, 32x32, 96x16

### 4. Show Clock

1. Go to the **"Clock"** tab
2. Select a clock style (0-8)
3. Click **"Show Clock"**

The clock will display the current time and update automatically.

### 5. Adjust Settings

Go to the **"Settings"** tab to:
- **Adjust brightness**: Drag the slider (1-100%) and click "Set Brightness"
- **Power control**: Turn the display ON or OFF

## Troubleshooting

### Device Not Found During Scan

- Ensure your LED panel is powered on
- Check that Bluetooth is enabled on your PC
- Make sure the panel is not connected to another device
- Try moving the panel closer to your PC
- Restart both the panel and your PC

### Connection Failed

- Ensure no other app is connected to the panel (close the official iPixel app)
- On Windows, go to Settings → Bluetooth & devices → Remove the device, then scan again
- Try disabling and re-enabling Bluetooth
- Make sure your Bluetooth adapter supports Bluetooth LE (Low Energy)

### Text/Image Not Displaying

- Check that you're connected (status shows "Connected" in green)
- Try reducing font size or text length
- Ensure image file is not corrupted
- Try power cycling the panel

### "ModuleNotFoundError" Error

- Ensure you've installed all dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### Slow Performance

- Close other Bluetooth applications
- Reduce image size before sending
- Move panel closer to PC for better signal

## Technical Details

### Supported Devices

This application works with LED panels using the iPixel Color protocol via Bluetooth LE:
- BGLight LED Pixel Boards
- B.K. Light LED Pixel Board (from Action stores)
- Generic LED_BLE_* devices
- iPixel Color compatible displays

### Protocol Information

- **Communication**: Bluetooth Low Energy (BLE)
- **Write UUID**: `0000fa02-0000-1000-8000-00805f9b34fb`
- **Notify UUID**: `0000fa03-0000-1000-8000-00805f9b34fb`
- **Library**: Built on [pypixelcolor](https://github.com/lucagoc/pypixelcolor)

## Development

### Project Structure

```
ipixel-controller/
├── ipixel_controller.py   # Main application
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Dependencies

- `pypixelcolor` - Core library for iPixel protocol
- `bleak` - Bluetooth Low Energy library
- `pillow` - Image processing

### Contributing

Feel free to submit issues or pull requests!

## Known Limitations

- Windows only (Linux/Mac support possible with modifications)
- Single device connection at a time
- Some advanced features from the official app may not be available
- Bluetooth range is limited (typically 10 meters)

## Credits

- Built on [pypixelcolor](https://github.com/lucagoc/pypixelcolor) by lucagoc
- Based on reverse-engineered iPixel protocol
- Thanks to the Home Assistant [ha-ipixel-color](https://github.com/cagcoach/ha-ipixel-color) project for protocol documentation

## License

This project is provided as-is for personal use. Not affiliated with iPixel or the original device manufacturers.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Verify you're using the latest version
3. Check the pypixelcolor documentation
4. Open an issue on GitHub (if applicable)

---

**Enjoy controlling your LED panel!** 🎉
