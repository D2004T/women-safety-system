"""
Women Safety System - Complete Web Application
Single file that runs everything: backend + frontend
Access via: http://localhost:5000 or http://your-ip:5000
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
import random
import math
from datetime import datetime
import json
import os
from pathlib import Path

# Try to import optional dependencies
try:
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except:
    VOICE_AVAILABLE = False

try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_AVAILABLE = True
except:
    FIREBASE_AVAILABLE = False

try:
    from telegram import Bot
    import asyncio
    TELEGRAM_AVAILABLE = True
except:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIGURATION ====================
class Config:
    # System Settings
    SIMULATION_MODE = True
    DISTRESS_KEYWORDS = ["help", "save me", "emergency", "danger", "police"]
    GPS_UPDATE_INTERVAL = 2  # seconds
    
    # Firebase (Optional - will work without it)
    FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "firebase-credentials.json")
    FIREBASE_DATABASE_URL = os.getenv("FIREBASE_URL", "https://your-project.firebaseio.com")
    
    # Telegram (Optional - will work without it)
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
    
    # Simulation
    SIMULATION_GPS_CENTER = (28.6139, 77.2090)  # Delhi
    SIMULATION_GPS_RADIUS = 0.01
    SIMULATION_VOICE_TRIGGER_PROB = 0.15

# ==================== FLASK APP SETUP ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'women-safety-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# ==================== GLOBAL STATE ====================
class SystemState:
    def __init__(self):
        self.running = False
        self.current_location = None
        self.current_status = "safe"
        self.events = []
        self.connected_clients = 0
        self.firebase_connected = False
        self.telegram_enabled = False
        
        # Simulation state
        self.sim_lat = Config.SIMULATION_GPS_CENTER[0]
        self.sim_lon = Config.SIMULATION_GPS_CENTER[1]
        self.sim_angle = 0

state = SystemState()

# ==================== GPS SIMULATION ====================
def get_simulated_gps():
    """Generate simulated GPS data"""
    state.sim_angle += random.uniform(-30, 30)
    distance = random.uniform(0, Config.SIMULATION_GPS_RADIUS * 0.1)
    
    state.sim_lat += distance * math.cos(math.radians(state.sim_angle))
    state.sim_lon += distance * math.sin(math.radians(state.sim_angle))
    
    # Keep within bounds
    center_lat, center_lon = Config.SIMULATION_GPS_CENTER
    max_dist = Config.SIMULATION_GPS_RADIUS
    
    if abs(state.sim_lat - center_lat) > max_dist:
        state.sim_lat = center_lat + (max_dist if state.sim_lat > center_lat else -max_dist)
    
    if abs(state.sim_lon - center_lon) > max_dist:
        state.sim_lon = center_lon + (max_dist if state.sim_lon > center_lon else -max_dist)
    
    return {
        'latitude': round(state.sim_lat, 6),
        'longitude': round(state.sim_lon, 6),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'accuracy': random.uniform(5, 15),
        'source': 'simulated'
    }

# ==================== VOICE SIMULATION ====================
def simulate_voice_detection():
    """Simulate voice detection"""
    if random.random() < Config.SIMULATION_VOICE_TRIGGER_PROB:
        keyword = random.choice(Config.DISTRESS_KEYWORDS)
        return True, keyword, 0.85
    return False, None, 0.0

# ==================== FIREBASE HANDLER ====================
class FirebaseHandler:
    def __init__(self):
        self.connected = False
        if FIREBASE_AVAILABLE and os.path.exists(Config.FIREBASE_CREDENTIALS):
            try:
                if not firebase_admin._apps:
                    cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS)
                    firebase_admin.initialize_app(cred, {
                        'databaseURL': Config.FIREBASE_DATABASE_URL
                    })
                self.db_ref = db.reference()
                self.connected = True
                print("✓ Firebase connected")
            except Exception as e:
                print(f"⚠ Firebase not available: {e}")
    
    def store_event(self, event_data):
        if not self.connected:
            return False
        try:
            self.db_ref.child('women_safety/events').push(event_data)
            self.db_ref.child('women_safety/status').set({
                'latitude': event_data['latitude'],
                'longitude': event_data['longitude'],
                'status': event_data['status'],
                'last_update': event_data['timestamp']
            })
            return True
        except:
            return False

firebase_handler = FirebaseHandler()
state.firebase_connected = firebase_handler.connected

# ==================== TELEGRAM HANDLER ====================
class TelegramHandler:
    def __init__(self):
        self.enabled = False
        if TELEGRAM_AVAILABLE and Config.TELEGRAM_BOT_TOKEN:
            try:
                self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
                self.enabled = True
                print("✓ Telegram bot enabled")
            except Exception as e:
                print(f"⚠ Telegram not available: {e}")
    
    async def send_alert(self, location, keyword):
        if not self.enabled:
            return False
        
        lat = location['latitude']
        lon = location['longitude']
        maps_link = f"https://www.google.com/maps?q={lat},{lon}"
        
        message = f"""
🚨 EMERGENCY ALERT 🚨

⚠️ Distress Keyword: "{keyword}"

📍 Location:
   {lat:.6f}, {lon:.6f}

🕐 Time: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}

🗺 Map: {maps_link}
"""
        
        success = False
        for chat_id in Config.TELEGRAM_CHAT_IDS:
            if chat_id:
                try:
                    await self.bot.send_message(chat_id=chat_id, text=message)
                    success = True
                except:
                    pass
        return success

telegram_handler = TelegramHandler()
state.telegram_enabled = telegram_handler.enabled

# ==================== MONITORING THREAD ====================
def monitoring_loop():
    """Main monitoring loop running in background"""
    print("🚀 Monitoring loop started")
    
    while state.running:
        try:
            # Get GPS location
            location = get_simulated_gps()
            state.current_location = location
            
            # Emit location update to all clients
            socketio.emit('location_update', location)
            
            # Check for distress
            detected, keyword, confidence = simulate_voice_detection()
            
            if detected:
                print(f"🚨 DISTRESS DETECTED: {keyword}")
                state.current_status = "distress"
                
                # Create event
                event = {
                    'latitude': location['latitude'],
                    'longitude': location['longitude'],
                    'timestamp': location['timestamp'],
                    'status': 'distress',
                    'keyword': keyword,
                    'accuracy': location['accuracy']
                }
                
                # Store event
                state.events.insert(0, event)
                if len(state.events) > 50:
                    state.events.pop()
                
                # Save to Firebase
                firebase_handler.store_event(event)
                
                # Send Telegram alert
                if telegram_handler.enabled:
                    try:
                        asyncio.run(telegram_handler.send_alert(location, keyword))
                    except:
                        pass
                
                # Emit emergency alert
                socketio.emit('emergency_alert', event)
                
                # Enhanced monitoring for 30 seconds
                for i in range(15):
                    location = get_simulated_gps()
                    socketio.emit('location_update', location)
                    time.sleep(2)
                
                state.current_status = "safe"
            
            else:
                # Store safe status periodically
                if len(state.events) % 10 == 0:
                    event = {
                        'latitude': location['latitude'],
                        'longitude': location['longitude'],
                        'timestamp': location['timestamp'],
                        'status': 'safe',
                        'accuracy': location['accuracy']
                    }
                    state.events.insert(0, event)
                    firebase_handler.store_event(event)
            
            # Update status
            socketio.emit('status_update', {
                'status': state.current_status,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            
            time.sleep(Config.GPS_UPDATE_INTERVAL)
        
        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            time.sleep(1)
    
    print("🛑 Monitoring loop stopped")

# ==================== FLASK ROUTES ====================
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current system status"""
    return jsonify({
        'running': state.running,
        'status': state.current_status,
        'location': state.current_location,
        'connected_clients': state.connected_clients,
        'firebase_connected': state.firebase_connected,
        'telegram_enabled': state.telegram_enabled,
        'total_events': len(state.events)
    })

@app.route('/api/events')
def get_events():
    """Get recent events"""
    limit = request.args.get('limit', 20, type=int)
    return jsonify({
        'events': state.events[:limit]
    })

@app.route('/api/start', methods=['POST'])
def start_system():
    """Start monitoring system"""
    if not state.running:
        state.running = True
        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
        return jsonify({'success': True, 'message': 'System started'})
    return jsonify({'success': False, 'message': 'Already running'})

@app.route('/api/stop', methods=['POST'])
def stop_system():
    """Stop monitoring system"""
    state.running = False
    return jsonify({'success': True, 'message': 'System stopped'})

@app.route('/api/trigger-emergency', methods=['POST'])
def trigger_emergency():
    """Manually trigger emergency (for testing)"""
    if state.current_location:
        event = {
            'latitude': state.current_location['latitude'],
            'longitude': state.current_location['longitude'],
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'status': 'distress',
            'keyword': 'MANUAL_TRIGGER',
            'accuracy': 10.0
        }
        state.events.insert(0, event)
        firebase_handler.store_event(event)
        socketio.emit('emergency_alert', event)
        return jsonify({'success': True, 'message': 'Emergency triggered'})
    return jsonify({'success': False, 'message': 'No location available'})

# ==================== SOCKETIO EVENTS ====================
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    state.connected_clients += 1
    print(f"✓ Client connected (total: {state.connected_clients})")
    
    # Send current state to new client
    if state.current_location:
        emit('location_update', state.current_location)
    
    emit('status_update', {
        'status': state.current_status,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    state.connected_clients -= 1
    print(f"✗ Client disconnected (total: {state.connected_clients})")

@socketio.on('request_location')
def handle_location_request():
    """Handle location request from client"""
    if state.current_location:
        emit('location_update', state.current_location)

# ==================== HTML TEMPLATE ====================
def create_templates():
    """Create templates directory and HTML file"""
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Women Safety System - Live Dashboard</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
            color: #fff;
            min-height: 100vh;
        }
        
        .header {
            background: #16213e;
            padding: 15px 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .header h1 {
            font-size: 1.5rem;
            color: #e91e63;
        }
        
        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            font-size: 0.9rem;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4caf50;
            animation: pulse 2s infinite;
        }
        
        .status-dot.emergency {
            background: #f44336;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 600;
        }
        
        .btn-start {
            background: #4caf50;
            color: white;
        }
        
        .btn-stop {
            background: #f44336;
            color: white;
        }
        
        .btn-emergency {
            background: #ff9800;
            color: white;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: #16213e;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }
        
        .stat-card h3 {
            font-size: 0.9rem;
            color: #b0b0b0;
            margin-bottom: 8px;
        }
        
        .stat-card .value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #e91e63;
        }
        
        .map-container {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }
        
        #map {
            height: 400px;
            border-radius: 8px;
            margin-top: 15px;
        }
        
        .events {
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }
        
        .events h2 {
            margin-bottom: 15px;
            color: #e91e63;
        }
        
        .event-item {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 6px;
            border-left: 4px solid #4caf50;
        }
        
        .event-item.emergency {
            border-left-color: #f44336;
        }
        
        .event-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-weight: bold;
        }
        
        .event-details {
            font-size: 0.9rem;
            color: #b0b0b0;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #b0b0b0;
            margin-top: 40px;
        }
        
        @media (max-width: 768px) {
            .header h1 { font-size: 1.2rem; }
            #map { height: 300px; }
            .stats { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ Women Safety System</h1>
        <div class="status-badge">
            <div class="status-dot" id="statusDot"></div>
            <span id="statusText">Safe</span>
        </div>
    </div>

    <div class="container">
        <div class="controls">
            <button class="btn btn-start" onclick="startSystem()" id="startBtn">▶️ Start Monitoring</button>
            <button class="btn btn-stop" onclick="stopSystem()" id="stopBtn" disabled>⏹️ Stop</button>
            <button class="btn btn-emergency" onclick="triggerEmergency()">🚨 Test Emergency</button>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3>Current Status</h3>
                <div class="value" id="currentStatus">SAFE</div>
            </div>
            <div class="stat-card">
                <h3>Location</h3>
                <div class="value" style="font-size: 1rem;" id="coordinates">--, --</div>
            </div>
            <div class="stat-card">
                <h3>Total Events</h3>
                <div class="value" id="eventCount">0</div>
            </div>
            <div class="stat-card">
                <h3>Connected</h3>
                <div class="value" style="font-size: 1rem;" id="connection">Connecting...</div>
            </div>
        </div>

        <div class="map-container">
            <h2>📍 Live Location Tracking</h2>
            <div id="map"></div>
        </div>

        <div class="events">
            <h2>📊 Recent Events</h2>
            <div id="eventsList">
                <p style="color: #b0b0b0; text-align: center; padding: 20px;">No events yet...</p>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>&copy; 2024 Women Safety System | Real-Time Tracking & SOS</p>
    </div>

    <script>
        const socket = io();
        
        const map = L.map('map').setView([28.6139, 77.2090], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        let currentMarker = null;
        
        socket.on('connect', () => {
            document.getElementById('connection').textContent = '✓ Connected';
            loadStatus();
            loadEvents();
        });
        
        socket.on('disconnect', () => {
            document.getElementById('connection').textContent = '✗ Disconnected';
        });
        
        socket.on('location_update', (location) => {
            updateLocation(location);
        });
        
        socket.on('status_update', (status) => {
            updateStatus(status);
        });
        
        socket.on('emergency_alert', (event) => {
            handleEmergency(event);
        });
        
        function updateLocation(location) {
            const { latitude, longitude } = location;
            
            document.getElementById('coordinates').textContent = 
                `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
            
            if (currentMarker) {
                map.removeLayer(currentMarker);
            }
            
            const icon = L.divIcon({
                html: '<div style="font-size: 2rem;">📍</div>',
                className: 'custom-marker',
                iconSize: [40, 40]
            });
            
            currentMarker = L.marker([latitude, longitude], { icon }).addTo(map);
            currentMarker.bindPopup(`
                <b>Current Location</b><br>
                ${latitude.toFixed(6)}, ${longitude.toFixed(6)}<br>
                <a href="https://www.google.com/maps?q=${latitude},${longitude}" target="_blank">Open in Google Maps</a>
            `);
            
            map.setView([latitude, longitude], 15);
        }
        
        function updateStatus(status) {
            const statusText = document.getElementById('statusText');
            const statusDot = document.getElementById('statusDot');
            const currentStatus = document.getElementById('currentStatus');
            
            if (status.status === 'distress') {
                statusText.textContent = '🚨 EMERGENCY';
                statusDot.classList.add('emergency');
                currentStatus.textContent = 'EMERGENCY';
                currentStatus.style.color = '#f44336';
            } else {
                statusText.textContent = 'Safe';
                statusDot.classList.remove('emergency');
                currentStatus.textContent = 'SAFE';
                currentStatus.style.color = '#4caf50';
            }
        }
        
        function handleEmergency(event) {
            addEventToList(event);
            
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification('🚨 Emergency Alert', {
                    body: `Distress keyword detected: "${event.keyword}"`,
                    icon: '🚨'
                });
            }
            
            if (currentMarker) {
                map.removeLayer(currentMarker);
            }
            
            const icon = L.divIcon({
                html: '<div style="font-size: 2rem;">🚨</div>',
                className: 'custom-marker',
                iconSize: [40, 40]
            });
            
            currentMarker = L.marker([event.latitude, event.longitude], { icon }).addTo(map);
            currentMarker.bindPopup(`
                <b>🚨 EMERGENCY</b><br>
                Keyword: "${event.keyword}"<br>
                ${event.latitude.toFixed(6)}, ${event.longitude.toFixed(6)}
            `).openPopup();
        }
        
        function addEventToList(event) {
            const eventsList = document.getElementById('eventsList');
            
            if (eventsList.querySelector('p')) {
                eventsList.innerHTML = '';
            }
            
            const eventItem = document.createElement('div');
            eventItem.className = `event-item ${event.status === 'distress' ? 'emergency' : ''}`;
            
            const time = new Date(event.timestamp).toLocaleString();
            
            eventItem.innerHTML = `
                <div class="event-header">
                    <span>${event.status === 'distress' ? '🚨 EMERGENCY' : '✓ Safe'}</span>
                    <span>${time}</span>
                </div>
                <div class="event-details">
                    ${event.keyword ? `Keyword: "${event.keyword}"<br>` : ''}
                    Location: ${event.latitude.toFixed(6)}, ${event.longitude.toFixed(6)}<br>
                    <a href="https://www.google.com/maps?q=${event.latitude},${event.longitude}" 
                       target="_blank" style="color: #e91e63;">View on Map →</a>
                </div>
            `;
            
            eventsList.insertBefore(eventItem, eventsList.firstChild);
            
            const count = eventsList.querySelectorAll('.event-item').length;
            document.getElementById('eventCount').textContent = count;
        }
        
        async function startSystem() {
            const response = await fetch('/api/start', { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
            }
        }
        
        async function stopSystem() {
            const response = await fetch('/api/stop', { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
            }
        }
        
        async function triggerEmergency() {
            await fetch('/api/trigger-emergency', { method: 'POST' });
        }
        
        async function loadStatus() {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.running) {
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
            }
            
            if (data.location) {
                updateLocation(data.location);
            }
        }
        
        async function loadEvents() {
            const response = await fetch('/api/events?limit=10');
            const data = await response.json();
            
            data.events.forEach(event => addEventToList(event));
        }
        
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
    </script>
</body>
</html>'''
    
    (templates_dir / 'index.html').write_text(html_content)
    print("✓ Templates created")

# ==================== MAIN ====================
if __name__ == '__main__':
    print("=" * 60)
    print("🛡️  WOMEN SAFETY SYSTEM - WEB APPLICATION")
    print("=" * 60)
    print(f"\n📋 Configuration:")
    print(f"   Simulation Mode: ON")
    print(f"   Firebase: {'✓ Connected' if state.firebase_connected else '⚠ Offline'}")
    print(f"   Telegram: {'✓ Enabled' if state.telegram_enabled else '⚠ Disabled'}")
    print(f"\n🌐 Starting web server...")
    print(f"   Local: http://localhost:5000")
    print(f"   Network: http://YOUR_IP:5000")
    print(f"\n💡 Access from mobile: Use your computer's IP address")
    print(f"   Example: http://192.168.1.100:5000")
    print(f"\n⚠️  Press Ctrl+C to stop\n")
    print("=" * 60)
    
    # Create templates
    create_templates()
    
    # Run Flask app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
