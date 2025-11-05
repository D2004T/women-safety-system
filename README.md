# AI-Based Women Safety Device with Real-Time Tracking & SOS

🛡️ Complete web application for women safety with voice detection simulation, GPS tracking, Firebase storage, Telegram alerts, and live web dashboard.

## 🌟 Features

- 🎤 **Voice Detection Simulation**: Distress keyword detection
- 📍 **GPS Tracking**: Real-time location tracking with live updates
- 🔥 **Firebase Integration**: Real-time database storage (optional)
- 📱 **Telegram Alerts**: Automatic SOS messages (optional)
- 🗺️ **Web Dashboard**: Live location tracking with OpenStreetMap
- 🎭 **Simulation Mode**: Fully functional without hardware
- 📱 **Mobile Responsive**: Works on phones, tablets, and laptops
- 🔴 **Live Updates**: Real-time WebSocket communication

## 🚀 Quick Start

### Option 1: Deploy to Render (Recommended)

Click the button below to deploy instantly:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Option 2: Run Locally

```bash
# Clone repository
git clone https://github.com/D2004T/women-safety-system.git
cd women-safety-system

# Install dependencies
pip install -r requirements.txt

# Run application
python app.py

# Access at: http://localhost:5000
```

## 📱 Access from Mobile

1. Find your computer's IP address
2. Access: `http://YOUR_IP:5000`
3. Works on any device on the same network

## 🎮 How to Use

1. **Open the dashboard** in your browser
2. **Click "Start Monitoring"** to begin tracking
3. **Watch live location updates** on the map
4. **Test emergency alerts** with the "Test Emergency" button
5. **View event history** in the events panel

## 🔧 Configuration (Optional)

### Firebase Setup
1. Create Firebase project
2. Download service account key
3. Set environment variables:
   ```bash
   export FIREBASE_CREDENTIALS=path/to/credentials.json
   export FIREBASE_URL=https://your-project.firebaseio.com
   ```

### Telegram Setup
1. Create bot with @BotFather
2. Get your chat ID from @userinfobot
3. Set environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN=your_bot_token
   export TELEGRAM_CHAT_IDS=chat_id1,chat_id2
   ```

## 📊 System Architecture

```
┌─────────────────┐
│  Web Dashboard  │ ← User Interface (Mobile/Laptop)
└────────┬────────┘
         │ WebSocket
┌────────▼────────┐
│  Flask Server   │ ← Backend Logic
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌───────┐ ┌──────┐ ┌─────────┐ ┌──────────┐
│  GPS  │ │Voice │ │Firebase │ │ Telegram │
│ Sim   │ │ Sim  │ │(Optional)│ │(Optional)│
└───────┘ └──────┘ └─────────┘ └──────────┘
```

## 🛠️ Technology Stack

- **Backend**: Python, Flask, Flask-SocketIO
- **Frontend**: HTML5, CSS3, JavaScript
- **Real-time**: WebSocket (Socket.IO)
- **Maps**: Leaflet.js + OpenStreetMap
- **Optional**: Firebase, Telegram Bot API

## 📸 Screenshots

### Dashboard
![Dashboard](https://via.placeholder.com/800x400?text=Live+Dashboard)

### Emergency Alert
![Emergency](https://via.placeholder.com/800x400?text=Emergency+Alert)

## 🔒 Security Notes

- Never commit credentials to repository
- Use environment variables for sensitive data
- Restrict Firebase database rules in production
- Keep Telegram bot token secure

## 📝 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 📧 Support

For issues and questions, please open an issue on GitHub.

## 🎯 Roadmap

- [ ] Add real hardware support (GPS module, microphone)
- [ ] Implement user authentication
- [ ] Add multiple user tracking
- [ ] Mobile app (React Native)
- [ ] SMS alerts integration
- [ ] Historical route playback
- [ ] Geofencing alerts

## 👥 Credits

Developed for Women Safety Initiative

---

**⚠️ Note**: This is a simulation system for demonstration purposes. For production use with real hardware, additional configuration is required.
