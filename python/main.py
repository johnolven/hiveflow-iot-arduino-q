"""
============================================================
ARDUINO UNO Q - MPU PYTHON (Qualcomm Dragonwing)
============================================================

Author: John Olven
Project: HiveFlow IoT Demo

This script runs on the Qualcomm Dragonwing Linux MPU.
- Receives data from MCU via Bridge
- Serves a web dashboard with Flask
- Sends data to external webhook via HTTP POST

Use with: Arduino App Lab

============================================================
"""

import json
import time
import threading
from datetime import datetime
from flask import Flask, render_template_string, jsonify
import requests

# ==================== CONFIGURATION ====================
# Webhook URL - Change this to your endpoint
WEBHOOK_URL = "https://api.hiveflow.ai/api/triggers/flow/YOUR_FLOW_ID/YOUR_TOKEN"

# Webhook send interval (seconds)
WEBHOOK_INTERVAL = 30

# Dashboard web port
DASHBOARD_PORT = 5000

# ==================== GLOBAL VARIABLES ====================
sensor_data = {
    "temperature": 0.0,
    "object_detected": False,
    "alert": False,
    "threshold": 30.0,
    "timestamp": "",
    "wifi_ip": "0.0.0.0"
}

# ==================== FLASK APP ====================
app = Flask(__name__)

# HTML Template for Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arduino UNO Q - IoT Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: white;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        
        h1 {
            text-align: center;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2rem;
        }
        .subtitle {
            text-align: center;
            color: #8892b0;
            margin-bottom: 30px;
            font-size: 0.9rem;
        }
        
        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255,255,255,0.05);
            padding: 10px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        .status-dot.online { background: #00ff88; }
        .status-dot.offline { background: #ff4757; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        .card.alert {
            border-color: #ff4757;
            background: rgba(255,71,87,0.1);
            animation: alertPulse 1s infinite;
        }
        @keyframes alertPulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(255,71,87,0.4); }
            50% { box-shadow: 0 0 20px 10px rgba(255,71,87,0.2); }
        }
        .card-icon { font-size: 2.5rem; margin-bottom: 10px; }
        .card-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .card-label { color: #8892b0; font-size: 0.9rem; }
        .card-status {
            margin-top: 10px;
            padding: 5px 15px;
            border-radius: 20px;
            display: inline-block;
            font-size: 0.8rem;
        }
        .card-status.normal { background: rgba(0,255,136,0.2); color: #00ff88; }
        .card-status.alert { background: rgba(255,71,87,0.2); color: #ff4757; }
        .card-status.detected { background: rgba(0,217,255,0.2); color: #00d9ff; }
        .card-status.clear { background: rgba(255,255,255,0.1); color: #8892b0; }
        
        .info-section {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .info-section h3 {
            margin-bottom: 15px;
            color: #00d9ff;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        .info-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .info-label { color: #8892b0; }
        
        .webhook-status {
            text-align: center;
            padding: 15px;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            font-size: 0.85rem;
            color: #8892b0;
        }
        
        footer {
            text-align: center;
            margin-top: 30px;
            color: #4a5568;
            font-size: 0.8rem;
        }
        
        @media (max-width: 600px) {
            .status-bar { flex-direction: column; text-align: center; }
            .info-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Arduino UNO Q Dashboard</h1>
        <p class="subtitle">Real-time IoT Monitor | Qualcomm Dragonwing + STM32</p>
        
        <div class="status-bar">
            <div class="status-indicator">
                <div class="status-dot online" id="statusDot"></div>
                <span id="statusText">Connected</span>
            </div>
            <div>
                <span style="color: #8892b0;">IP:</span> 
                <span id="ipAddress">{{ ip }}</span>
            </div>
            <div>
                <span style="color: #8892b0;">Updated:</span>
                <span id="timestamp">--:--:--</span>
            </div>
        </div>
        
        <div class="cards">
            <div class="card" id="tempCard">
                <div class="card-icon">🌡️</div>
                <div class="card-value" id="temperature">--</div>
                <div class="card-label">Temperature (HW-498)</div>
                <div class="card-status normal" id="tempStatus">Normal</div>
            </div>
            
            <div class="card" id="sensorCard">
                <div class="card-icon">👁️</div>
                <div class="card-value" id="sensorValue">--</div>
                <div class="card-label">Photo Sensor (HW-487)</div>
                <div class="card-status clear" id="sensorStatus">Path clear</div>
            </div>
        </div>
        
        <div class="info-section">
            <h3>📊 System Information</h3>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Alert Threshold</span>
                    <span id="threshold">30.0 °C</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Device</span>
                    <span>Arduino UNO Q</span>
                </div>
                <div class="info-item">
                    <span class="info-label">MPU</span>
                    <span>Qualcomm QRB2210</span>
                </div>
                <div class="info-item">
                    <span class="info-label">MCU</span>
                    <span>STM32U585</span>
                </div>
            </div>
        </div>
        
        <div class="webhook-status">
            📡 Sending data to webhook every {{ interval }} seconds
            <br>
            <small>URL: {{ webhook_url[:50] }}...</small>
        </div>
        
        <footer>
            Arduino UNO Q IoT Dashboard | Powered by Flask + Python | HiveFlow Demo
        </footer>
    </div>
    
    <script>
        function updateDashboard() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    // Temperature
                    document.getElementById('temperature').textContent = data.temperature.toFixed(1) + ' °C';
                    const tempCard = document.getElementById('tempCard');
                    const tempStatus = document.getElementById('tempStatus');
                    
                    if (data.alert) {
                        tempCard.classList.add('alert');
                        tempStatus.textContent = '⚠️ ALERT';
                        tempStatus.className = 'card-status alert';
                    } else {
                        tempCard.classList.remove('alert');
                        tempStatus.textContent = '✓ Normal';
                        tempStatus.className = 'card-status normal';
                    }
                    
                    // Sensor
                    const sensorValue = document.getElementById('sensorValue');
                    const sensorStatus = document.getElementById('sensorStatus');
                    
                    if (data.object_detected) {
                        sensorValue.textContent = '🚫';
                        sensorStatus.textContent = 'Object detected';
                        sensorStatus.className = 'card-status detected';
                    } else {
                        sensorValue.textContent = '✅';
                        sensorStatus.textContent = 'Path clear';
                        sensorStatus.className = 'card-status clear';
                    }
                    
                    // Timestamp
                    document.getElementById('timestamp').textContent = data.timestamp;
                    document.getElementById('threshold').textContent = data.threshold + ' °C';
                    
                    // Status
                    document.getElementById('statusDot').classList.remove('offline');
                    document.getElementById('statusDot').classList.add('online');
                    document.getElementById('statusText').textContent = 'Connected';
                })
                .catch(err => {
                    document.getElementById('statusDot').classList.remove('online');
                    document.getElementById('statusDot').classList.add('offline');
                    document.getElementById('statusText').textContent = 'Disconnected';
                });
        }
        
        // Update every 2 seconds
        setInterval(updateDashboard, 2000);
        updateDashboard();
    </script>
</body>
</html>
"""

# ==================== FLASK ROUTES ====================

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template_string(
        DASHBOARD_HTML,
        ip=sensor_data['wifi_ip'],
        webhook_url=WEBHOOK_URL,
        interval=WEBHOOK_INTERVAL
    )

@app.route('/api/data')
def api_data():
    """API endpoint to get data in JSON"""
    return jsonify(sensor_data)

@app.route('/api/status')
def api_status():
    """System status"""
    return jsonify({
        "status": "online",
        "device": "Arduino UNO Q",
        "mpu": "Qualcomm QRB2210",
        "mcu": "STM32U585"
    })

# ==================== FUNCTIONS ====================

def get_local_ip():
    """Get local IP of UNO Q"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def send_webhook():
    """Send data to external webhook"""
    global sensor_data
    
    while True:
        try:
            payload = {
                "device": "Arduino UNO Q",
                "temperature": sensor_data['temperature'],
                "object_detected": sensor_data['object_detected'],
                "alert": sensor_data['alert'],
                "threshold": sensor_data['threshold'],
                "timestamp": sensor_data['timestamp'],
                "ip": sensor_data['wifi_ip']
            }
            
            response = requests.post(
                WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"[Webhook] Sent: {response.status_code}")
            
        except Exception as e:
            print(f"[Webhook] Error: {e}")
        
        time.sleep(WEBHOOK_INTERVAL)

def read_mcu_data():
    """
    Read data from MCU via Bridge
    In App Lab, this is done automatically via Bridge RPC
    This is a simplified example
    """
    global sensor_data
    
    # In Arduino App Lab, you would use:
    # from arduino import Arduino
    # arduino = Arduino()
    # data = arduino.serial_read()
    
    # For now, we simulate reading
    # In production, this reads from the real Bridge
    
    import random
    
    while True:
        try:
            # Simulate data (in production, read from Bridge)
            sensor_data['temperature'] = round(random.uniform(20, 35), 1)
            sensor_data['object_detected'] = random.random() > 0.7
            sensor_data['alert'] = sensor_data['temperature'] >= sensor_data['threshold']
            sensor_data['timestamp'] = datetime.now().strftime("%H:%M:%S")
            
        except Exception as e:
            print(f"[MCU] Error: {e}")
        
        time.sleep(1)

# ==================== MAIN ====================

def main():
    """Main function"""
    print("=" * 50)
    print("Arduino UNO Q - IoT Dashboard")
    print("=" * 50)
    
    # Get IP
    sensor_data['wifi_ip'] = get_local_ip()
    print(f"Local IP: {sensor_data['wifi_ip']}")
    print(f"Dashboard: http://{sensor_data['wifi_ip']}:{DASHBOARD_PORT}")
    print(f"Webhook: {WEBHOOK_URL}")
    print("=" * 50)
    
    # Start thread to read MCU data
    mcu_thread = threading.Thread(target=read_mcu_data, daemon=True)
    mcu_thread.start()
    
    # Start thread for webhook
    webhook_thread = threading.Thread(target=send_webhook, daemon=True)
    webhook_thread.start()
    
    # Start Flask server
    print(f"\n🌐 Dashboard available at:")
    print(f"   Local:   http://localhost:{DASHBOARD_PORT}")
    print(f"   Network: http://{sensor_data['wifi_ip']}:{DASHBOARD_PORT}")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(
        host='0.0.0.0',
        port=DASHBOARD_PORT,
        debug=False,
        threaded=True
    )

if __name__ == "__main__":
    main()
