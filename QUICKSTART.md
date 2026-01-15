# Quick Start Guide - iPixel LED Controller

## 🚀 Quick Installation (Windows)

### Step 1: Install Python
1. Download Python from: https://www.python.org/downloads/
2. **IMPORTANT**: During installation, check ☑️ "Add Python to PATH"
3. Complete the installation

### Step 2: Download the Application
1. Download all files to a folder (e.g., `C:\iPixel`)
2. You should have these files:
   - `ipixel_controller.py`
   - `requirements.txt`
   - `run.bat`
   - `README.md`

### Step 3: Run the Application
1. Double-click `run.bat` in the folder
2. First time: It will automatically install dependencies (takes 1-2 minutes)
3. The application window will open

### Step 4: Connect Your LED Panel
1. Turn on your iPixel LED panel
2. In the app, click **"Scan"**
3. Select your device (usually "LED_BLE_...")
4. Click **"Connect"**
5. Wait for green "Connected" status

### Step 5: Start Using It!
- **Text Tab**: Send custom text with colors
- **Image Tab**: Display images
- **Clock Tab**: Show time
- **Settings Tab**: Adjust brightness and power

## 🔧 Alternative: Manual Installation

If `run.bat` doesn't work, follow these steps:

1. Open Command Prompt (Win+R, type `cmd`, press Enter)

2. Navigate to your folder:
   ```
   cd C:\iPixel
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python ipixel_controller.py
   ```

## ❗ Troubleshooting

### "Python is not recognized"
- You didn't check "Add Python to PATH" during installation
- Solution: Reinstall Python and make sure to check that box

### "pip is not recognized"
- Reinstall Python with "Add Python to PATH" checked
- Or use: `python -m pip install -r requirements.txt`

### Device Not Found
- Panel must be powered on
- Close official iPixel app if running
- Try scanning again
- Move panel closer to PC

### Connection Timeout
- Remove device from Windows Bluetooth settings first
- Then scan and connect through the app
- Make sure no other device is connected to the panel

### Import Errors
- Run: `pip install pypixelcolor bleak pillow`
- Restart the application

## 📝 Quick Tips

1. **First connection** may take 10-20 seconds
2. **Keep panel close** to PC for best connection
3. **Short text** displays better on small panels
4. **Image resolution**: Match your panel size for best results
5. **Brightness**: Start at 50% and adjust

## 🎯 Common Panel Sizes

- **64x64 pixels**: Good for images and detailed text
- **32x32 pixels**: Suitable for short text and simple images
- **96x16 pixels**: Perfect for scrolling text
- **20x64 pixels**: Wide format for text

## 🆘 Need Help?

1. Check the full README.md for detailed instructions
2. Verify Bluetooth is enabled on your PC
3. Make sure panel is charged/powered
4. Try restarting both panel and PC
5. Update Python to the latest version

## ✅ System Requirements

- Windows 10 or 11
- Python 3.8 or higher
- Bluetooth LE adapter
- 50 MB free disk space

---

**You're all set! Enjoy your LED panel! 🎨**
