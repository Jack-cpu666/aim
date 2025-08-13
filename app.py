from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
import json

app = Flask(__name__)

# Store visited zones in memory (in production, use a database)
visited_zones = {}

# All zones from the screenshots organized by floor
zones_data = {
    'Basement': [
        {'id': '10151853', 'location': 'Basement Interior', 'visited': False}
    ],
    'Floor 2': [
        {'id': '10151808', 'location': 'Catwalk Stairwell', 'visited': False},
        {'id': '10150864', 'location': 'East Stairwell', 'visited': False},
        {'id': '10151804', 'location': 'Gym', 'visited': False},
        {'id': '10150871', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 3': [
        {'id': '10151833', 'location': 'Patio & Lounge', 'visited': False},
        {'id': '10150882', 'location': 'West Stairwell', 'visited': False},
        {'id': '10150874', 'location': 'Catwalk Stairwell', 'visited': False}
    ],
    'Floor 4': [
        {'id': '10151806', 'location': 'Catwalk Stairwell', 'visited': False},
        {'id': '10151844', 'location': 'East Stairwell', 'visited': False},
        {'id': '10151851', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 5': [
        {'id': '10151848', 'location': 'Catwalk Stairwell', 'visited': False},
        {'id': '10151839', 'location': 'East Stairwell', 'visited': False},
        {'id': '10151815', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 6': [
        {'id': '10151834', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10151842', 'location': 'East Stairwell', 'visited': False},
        {'id': '10150866', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 7': [
        {'id': '10150873', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10151819', 'location': 'East Stairwell', 'visited': False},
        {'id': '10151811', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 8': [
        {'id': '10150867', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10151814', 'location': 'East', 'visited': False},
        {'id': '10151835', 'location': 'West', 'visited': False}
    ],
    'Floor 9': [
        {'id': '10150881', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10150885', 'location': 'East', 'visited': False},
        {'id': '10150887', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 10': [
        {'id': '10150865', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10151807', 'location': 'East', 'visited': False},
        {'id': '10151852', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 11': [
        {'id': '10151805', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10151825', 'location': 'East', 'visited': False},
        {'id': '10151816', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 12': [
        {'id': '10150880', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10150884', 'location': 'East Stairwell', 'visited': False},
        {'id': '10151829', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 14': [
        {'id': '10150889', 'location': 'Alley Stairwell', 'visited': False},
        {'id': '10150875', 'location': 'East', 'visited': False},
        {'id': '10151818', 'location': 'West Stairwell', 'visited': False}
    ],
    'Floor 15': [
        {'id': '10151837', 'location': '15th Floor', 'visited': False},
        {'id': '10151827', 'location': 'Alley Stairwell', 'visited': False}
    ],
    'Floor 16': [
        {'id': '10151847', 'location': 'Penthouse', 'visited': False}
    ],
    'Floor 17': [
        {'id': '10150879', 'location': 'Floor 17', 'visited': False}
    ]
}

# Custom zones added by users
custom_zones = {}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>NFC Tour Checkpoint System - Plaza 555</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e1e2e 0%, #151521 100%);
            color: #fff;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .header {
            background: linear-gradient(135deg, #ff6b35 0%, #ff4500 100%);
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header h1 {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .tour-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
        }

        .tour-name {
            font-size: 14px;
            opacity: 0.95;
        }

        .add-tag-btn {
            background: rgba(0,0,0,0.3);
            border: 2px solid rgba(255,255,255,0.3);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
        }

        .add-tag-btn:hover {
            background: rgba(255,255,255,0.2);
            border-color: white;
        }

        .progress-container {
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            padding: 10px;
            margin-top: 15px;
        }

        .progress-text {
            font-size: 14px;
            margin-bottom: 8px;
            font-weight: 600;
        }

        .progress-bar {
            width: 100%;
            height: 10px;
            background: rgba(255,255,255,0.2);
            border-radius: 5px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            transition: width 0.5s ease;
            border-radius: 5px;
        }

        .tabs-container {
            background: rgba(0,0,0,0.2);
            padding: 10px;
            display: flex;
            overflow-x: auto;
            gap: 8px;
            border-bottom: 2px solid rgba(255,255,255,0.1);
            position: sticky;
            top: 170px;
            z-index: 90;
            backdrop-filter: blur(10px);
        }

        .tabs-container::-webkit-scrollbar {
            height: 4px;
        }

        .tabs-container::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.1);
        }

        .tabs-container::-webkit-scrollbar-thumb {
            background: #ff6b35;
            border-radius: 2px;
        }

        .tab-btn {
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border: none;
            color: #fff;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            white-space: nowrap;
            transition: all 0.3s;
            flex-shrink: 0;
        }

        .tab-btn.active {
            background: #ff6b35;
            transform: scale(1.05);
        }

        .tab-btn:hover {
            background: rgba(255,107,53,0.8);
        }

        .tab-content {
            display: none;
            padding: 20px;
            animation: fadeIn 0.5s;
        }

        .tab-content.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .zone-card {
            background: linear-gradient(135deg, #2a2a3e 0%, #1a1a2e 100%);
            border-radius: 15px;
            margin-bottom: 15px;
            padding: 20px;
            border: 2px solid rgba(255,255,255,0.1);
            position: relative;
            overflow: hidden;
            transition: all 0.3s;
        }

        .zone-card.custom {
            background: linear-gradient(135deg, #3e2a3e 0%, #2e1a2e 100%);
            border-color: rgba(255,107,53,0.3);
        }

        .zone-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #ff6b35, #ff4500);
            transform: scaleX(0);
            transition: transform 0.3s;
        }

        .zone-card:hover::before {
            transform: scaleX(1);
        }

        .zone-card.visited {
            background: linear-gradient(135deg, #1a3d1a 0%, #0d260d 100%);
            border-color: #4CAF50;
        }

        .zone-card.visited::before {
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            transform: scaleX(1);
        }

        .zone-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .zone-title {
            font-size: 18px;
            font-weight: 700;
            color: #fff;
        }

        .nfc-id {
            font-family: 'SF Mono', 'Courier New', monospace;
            font-size: 14px;
            background: rgba(255,255,255,0.1);
            padding: 5px 10px;
            border-radius: 8px;
            color: #ff6b35;
        }

        .zone-location {
            font-size: 16px;
            color: rgba(255,255,255,0.8);
            margin-bottom: 20px;
        }

        .write-btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #ff6b35 0%, #ff4500 100%);
            border: none;
            color: white;
            font-size: 16px;
            font-weight: 700;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 1px;
            position: relative;
            overflow: hidden;
        }

        .write-btn::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255,255,255,0.3);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }

        .write-btn:active::after {
            width: 300px;
            height: 300px;
        }

        .write-btn:active {
            transform: scale(0.98);
        }

        .write-btn.success {
            background: linear-gradient(135deg, #4CAF50, #8BC34A);
            animation: pulse 0.5s;
        }

        .write-btn.writing {
            background: linear-gradient(135deg, #2196F3, #03A9F4);
            animation: breathing 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        @keyframes breathing {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }

        .status-badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 10px;
        }

        .status-badge.visited {
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
            border: 1px solid #4CAF50;
        }

        .status-badge.not-visited {
            background: rgba(255, 107, 53, 0.2);
            color: #ff6b35;
            border: 1px solid #ff6b35;
        }

        .status-badge.custom {
            background: rgba(156, 39, 176, 0.2);
            color: #9c27b0;
            border: 1px solid #9c27b0;
        }

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: linear-gradient(135deg, #2a2a3e 0%, #1a1a2e 100%);
            padding: 30px;
            border-radius: 20px;
            text-align: center;
            max-width: 90%;
            width: 400px;
            animation: slideUp 0.3s;
        }

        @keyframes slideUp {
            from { transform: translateY(50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .nfc-icon {
            width: 100px;
            height: 100px;
            margin: 20px auto;
            border: 3px solid #ff6b35;
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 48px;
            animation: nfcPulse 2s infinite;
        }

        @keyframes nfcPulse {
            0%, 100% { transform: scale(1); border-color: #ff6b35; }
            50% { transform: scale(1.1); border-color: #ff4500; }
        }

        .add-tag-modal .modal-content {
            text-align: left;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #ff6b35;
            font-weight: 600;
        }

        .form-group input, .form-group select {
            width: 100%;
            padding: 12px;
            background: rgba(255,255,255,0.1);
            border: 2px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            color: white;
            font-size: 16px;
        }

        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #ff6b35;
            background: rgba(255,255,255,0.15);
        }

        .modal-buttons {
            display: flex;
            gap: 10px;
            justify-content: space-between;
            margin-top: 20px;
        }

        .modal-buttons button {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-cancel {
            background: rgba(255,255,255,0.1);
            color: white;
        }

        .btn-save {
            background: linear-gradient(135deg, #ff6b35, #ff4500);
            color: white;
        }

        .error-message {
            background: linear-gradient(135deg, #f44336, #e91e63);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin: 20px;
            display: none;
            animation: shake 0.5s;
        }

        .error-message.show {
            display: block;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }

        .stats-container {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin: 20px;
        }

        .stat-card {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }

        .stat-number {
            font-size: 24px;
            font-weight: 700;
            color: #ff6b35;
        }

        .stat-label {
            font-size: 12px;
            color: rgba(255,255,255,0.6);
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏢 Plaza 555 Security Tour</h1>
        <div class="tour-info">
            <div class="tour-name">Grave Shift Daily Tour - Interior/Parking</div>
            <button class="add-tag-btn" onclick="openAddTagModal()">➕ Add Custom Tag</button>
        </div>
        <div class="progress-container">
            <div class="progress-text">Progress: <span id="progressText">0%</span> (<span id="visitedCount">0</span>/<span id="totalCount">0</span> zones)</div>
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar"></div>
            </div>
        </div>
    </div>

    <div class="tabs-container">
        {% for floor in zones_data.keys() %}
        <button class="tab-btn {% if loop.first %}active{% endif %}" onclick="showTab('{{ floor }}')">{{ floor }}</button>
        {% endfor %}
    </div>

    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-number" id="currentFloorCount">0</div>
            <div class="stat-label">Current Floor Zones</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="remainingCount">0</div>
            <div class="stat-label">Remaining Total</div>
        </div>
    </div>

    {% for floor, zones in zones_data.items() %}
    <div class="tab-content {% if loop.first %}active{% endif %}" id="tab-{{ floor }}">
        <div id="zones-{{ floor.replace(' ', '-') }}">
            {% for zone in zones %}
            <div class="zone-card" id="zone-{{ zone.id }}">
                <div class="zone-header">
                    <div class="zone-title">Plaza 555 - Main Building</div>
                    <div class="nfc-id" title="This ID will be written to the NFC tag">NFC: {{ zone.id }}</div>
                </div>
                <div class="zone-location">📍 {{ floor }} > {{ zone.location }}</div>
                <button class="write-btn" onclick="writeNFC('{{ zone.id }}', '{{ floor }}', '{{ zone.location }}')">
                    📱 Write "{{ zone.id }}" to NFC Tag
                </button>
                <span class="status-badge not-visited" id="status-{{ zone.id }}">Not Visited</span>
            </div>
            {% endfor %}
        </div>
    </div>
    {% endfor %}

    <!-- NFC Write Modal -->
    <div class="modal" id="nfcModal">
        <div class="modal-content">
            <h2 style="color: #ff6b35; margin-bottom: 20px;">NFC Write Operation</h2>
            <div class="nfc-icon">📡</div>
            <p id="modalMessage" style="margin-bottom: 20px;">Hold your NFC tag near the device to write the zone ID...</p>
            <button class="write-btn" onclick="closeModal()">Cancel</button>
        </div>
    </div>

    <!-- Add Tag Modal -->
    <div class="modal add-tag-modal" id="addTagModal">
        <div class="modal-content">
            <h2 style="color: #ff6b35; margin-bottom: 20px;">Add Custom NFC Tag</h2>
            <div class="form-group">
                <label for="tagId">Tag ID (10-digit number)</label>
                <input type="text" id="tagId" placeholder="e.g., 10151999" maxlength="8" pattern="[0-9]{8}">
            </div>
            <div class="form-group">
                <label for="tagLocation">Location Name</label>
                <input type="text" id="tagLocation" placeholder="e.g., Security Office">
            </div>
            <div class="form-group">
                <label for="tagFloor">Floor</label>
                <select id="tagFloor">
                    {% for floor in zones_data.keys() %}
                    <option value="{{ floor }}">{{ floor }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="modal-buttons">
                <button class="btn-cancel" onclick="closeAddTagModal()">Cancel</button>
                <button class="btn-save" onclick="saveCustomTag()">Save Tag</button>
            </div>
        </div>
    </div>

    <div class="error-message" id="errorMessage"></div>

    <script>
        let currentTab = '{{ zones_data.keys()|first }}';
        let visitedZones = new Set();
        let totalZones = {{ total_zones }};
        let customZonesData = {};

        function showTab(floor) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById('tab-' + floor).classList.add('active');
            event.target.classList.add('active');
            currentTab = floor;
            
            updateFloorStats(floor);
        }

        function updateFloorStats(floor) {
            const floorZones = document.querySelectorAll(`#tab-${floor} .zone-card`);
            const visitedFloorZones = document.querySelectorAll(`#tab-${floor} .zone-card.visited`);
            document.getElementById('currentFloorCount').textContent = `${visitedFloorZones.length}/${floorZones.length}`;
        }

        async function writeNFC(zoneId, floor, location) {
            const card = document.getElementById('zone-' + zoneId);
            const btn = card.querySelector('.write-btn');
            const statusBadge = document.getElementById('status-' + zoneId);
            
            // Check for Web NFC support
            if (!('NDEFReader' in window)) {
                showError('Web NFC is not supported. Please use Chrome on Android with NFC enabled.');
                return;
            }
            
            try {
                // Show modal
                document.getElementById('nfcModal').classList.add('active');
                btn.classList.add('writing');
                btn.innerHTML = '⏳ Initializing NFC...';
                
                const ndef = new NDEFReader();
                
                // First, we need to scan to detect a tag
                btn.innerHTML = '⏳ Scanning for tag...';
                document.getElementById('modalMessage').innerHTML = `
                    <strong>Ready to write: ${zoneId}</strong><br>
                    Hold your NFC tag near the device...
                `;
                
                // Start scanning for tags
                await ndef.scan();
                
                // Set up one-time listener for when tag is detected
                await new Promise((resolve, reject) => {
                    const abortController = new AbortController();
                    const timeout = setTimeout(() => {
                        abortController.abort();
                        reject(new Error('Timeout waiting for tag'));
                    }, 30000); // 30 second timeout
                    
                    ndef.addEventListener('reading', async (event) => {
                        clearTimeout(timeout);
                        btn.innerHTML = '⏳ Writing to tag...';
                        document.getElementById('modalMessage').innerHTML = `
                            <strong>Tag detected!</strong><br>
                            Writing: ${zoneId}
                        `;
                        
                        try {
                            // Simple write - just the zone ID number
                            await ndef.write(zoneId);
                            
                            // Success!
                            btn.innerHTML = '✅ WRITTEN!';
                            document.getElementById('modalMessage').innerHTML = `
                                <strong style="color: #4CAF50;">✅ Successfully Written!</strong><br>
                                NFC Tag ID: <span style="font-family: monospace; font-size: 20px;">${zoneId}</span><br>
                                <small>${location} - ${new Date().toLocaleTimeString()}</small>
                            `;
                            
                            markAsVisited(zoneId, card, btn, statusBadge);
                            
                            setTimeout(() => {
                                closeModal();
                            }, 2000);
                            
                            resolve();
                        } catch (writeError) {
                            reject(writeError);
                        }
                    }, { once: true, signal: abortController.signal });
                    
                    ndef.addEventListener('readingerror', () => {
                        clearTimeout(timeout);
                        reject(new Error('Tag reading error - try a different tag'));
                    }, { once: true, signal: abortController.signal });
                });
                
            } catch (error) {
                console.error('NFC operation failed:', error);
                btn.classList.remove('writing');
                btn.innerHTML = '📱 Write to NFC Tag';
                closeModal();
                
                if (error.name === 'NotAllowedError') {
                    showError('NFC permission denied. Please allow NFC access and try again.');
                } else if (error.name === 'AbortError' || error.message.includes('Timeout')) {
                    showError('NFC operation timed out. Make sure NFC is enabled and try again.');
                } else if (error.name === 'NotSupportedError') {
                    showError('Your device does not support NFC or it is disabled.');
                } else if (error.name === 'SecurityError') {
                    showError('NFC requires HTTPS. Please use a secure connection.');
                } else if (error.name === 'NetworkError') {
                    showError('NFC hardware error. Check if NFC is enabled in your device settings.');
                } else {
                    showError(`NFC Error: ${error.message}`);
                }
            }
        }
                }
            }
        }
        
        // Optional: Add NFC reading capability to verify writes
        async function readNFC() {
            if (!('NDEFReader' in window)) {
                showError('Web NFC is not supported on this device.');
                return;
            }
            
            try {
                const ndef = new NDEFReader();
                await ndef.scan();
                
                ndef.addEventListener('reading', event => {
                    const decoder = new TextDecoder();
                    
                    for (const record of event.message.records) {
                        console.log('Record type:', record.recordType);
                        
                        // Read the zone ID from the tag
                        const data = decoder.decode(record.data);
                        console.log('Tag data:', data);
                        
                        // Check if this matches one of our zone IDs (8 digits starting with 10)
                        if (/^10\d{6}$/.test(data)) {
                            const card = document.getElementById('zone-' + data);
                            if (card) {
                                showSuccess(`✅ Tag verified: Zone ${data}`);
                                
                                // Auto-mark as visited if not already
                                if (!card.classList.contains('visited')) {
                                    const btn = card.querySelector('.write-btn');
                                    const statusBadge = document.getElementById('status-' + data);
                                    markAsVisited(data, card, btn, statusBadge);
                                }
                            } else {
                                showSuccess(`Tag read: ${data} (not in current tour)`);
                            }
                        }
                    }
                });
                
                ndef.addEventListener('readingerror', () => {
                    showError('Cannot read data from the NFC tag.');
                });
                
            } catch (error) {
                showError(`Read error: ${error.message}`);
            }
        }

        function markAsVisited(zoneId, card, btn, statusBadge) {
            card.classList.add('visited');
            btn.classList.remove('writing');
            btn.classList.add('success');
            btn.innerHTML = `✅ "${zoneId}" WRITTEN`;
            statusBadge.textContent = 'Visited at ' + new Date().toLocaleTimeString();
            statusBadge.classList.remove('not-visited');
            statusBadge.classList.add('visited');
            
            visitedZones.add(zoneId);
            updateProgress();
            updateFloorStats(currentTab);
            
            // Send to server
            fetch('/mark_visited', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({zoneId: zoneId})
            });
        }



        function updateProgress() {
            const visited = visitedZones.size;
            const percent = Math.round((visited / totalZones) * 100);
            
            document.getElementById('visitedCount').textContent = visited;
            document.getElementById('totalCount').textContent = totalZones;
            document.getElementById('progressText').textContent = percent + '%';
            document.getElementById('progressBar').style.width = percent + '%';
            document.getElementById('remainingCount').textContent = totalZones - visited;
        }

        function closeModal() {
            document.getElementById('nfcModal').classList.remove('active');
        }

        function openAddTagModal() {
            document.getElementById('addTagModal').classList.add('active');
        }

        function closeAddTagModal() {
            document.getElementById('addTagModal').classList.remove('active');
            // Clear form
            document.getElementById('tagId').value = '';
            document.getElementById('tagLocation').value = '';
        }

        function saveCustomTag() {
            const tagId = document.getElementById('tagId').value;
            const tagLocation = document.getElementById('tagLocation').value;
            const tagFloor = document.getElementById('tagFloor').value;
            
            if (!tagId || !tagLocation) {
                showError('Please fill in all fields');
                return;
            }
            
            if (!/^\d{8}$/.test(tagId)) {
                showError('Tag ID must be exactly 8 digits');
                return;
            }
            
            // Send to server
            fetch('/add_custom_tag', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    id: tagId,
                    location: tagLocation,
                    floor: tagFloor
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Add to current floor
                    addTagToFloor(tagId, tagLocation, tagFloor);
                    closeAddTagModal();
                    showTab(tagFloor);
                    totalZones++;
                    updateProgress();
                    showSuccess('Custom tag added successfully!');
                } else {
                    showError('Failed to add tag');
                }
            });
        }

        function addTagToFloor(tagId, location, floor) {
            const floorContainer = document.getElementById('zones-' + floor.replace(' ', '-'));
            if (floorContainer) {
                const newCard = document.createElement('div');
                newCard.className = 'zone-card custom';
                newCard.id = 'zone-' + tagId;
                newCard.innerHTML = `
                    <div class="zone-header">
                        <div class="zone-title">Plaza 555 - Custom Zone</div>
                        <div class="nfc-id">NFC: ${tagId}</div>
                    </div>
                    <div class="zone-location">📍 ${floor} > ${location}</div>
                    <button class="write-btn" onclick="writeNFC('${tagId}', '${floor}', '${location}')">
                        📱 Write "${tagId}" to NFC Tag
                    </button>
                    <span class="status-badge custom" id="status-${tagId}">Custom Tag - Not Visited</span>
                `;
                floorContainer.appendChild(newCard);
            }
        }

        function showError(message) {
            const errorEl = document.getElementById('errorMessage');
            errorEl.textContent = message;
            errorEl.classList.add('show');
            setTimeout(() => errorEl.classList.remove('show'), 5000);
        }

        function showSuccess(message) {
            const errorEl = document.getElementById('errorMessage');
            errorEl.textContent = message;
            errorEl.style.background = 'linear-gradient(135deg, #4CAF50, #8BC34A)';
            errorEl.classList.add('show');
            setTimeout(() => {
                errorEl.classList.remove('show');
                errorEl.style.background = '';
            }, 5000);
        }

        // Initialize on load
        document.addEventListener('DOMContentLoaded', async function() {
            updateProgress();
            updateFloorStats(currentTab);
            
            // Check for NFC support and capabilities
            if ('NDEFReader' in window) {
                console.log('✅ Web NFC API is supported!');
                
                // Check if we're on HTTPS (required for Web NFC)
                if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
                    showError('Web NFC requires HTTPS. Please use a secure connection.');
                }
                
                // Add NFC status indicator
                const header = document.querySelector('.header');
                const nfcStatus = document.createElement('div');
                nfcStatus.style.cssText = 'background: rgba(0,0,0,0.3); padding: 8px; border-radius: 8px; margin-top: 10px; font-size: 12px;';
                nfcStatus.innerHTML = `
                    <span style="color: #4CAF50;">✅ NFC Ready</span> | 
                    <button onclick="startContinuousRead()" style="background: #4CAF50; border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer; margin: 0 4px;">
                        📡 Start Reading Mode
                    </button>
                    <button onclick="testReadTag()" style="background: #2196F3; border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer;">
                        🔍 Test Read Tag
                    </button>
                `;
                header.appendChild(nfcStatus);
                
                // Try to request NFC permission early (Chrome 89+)
                if ('permissions' in navigator) {
                    try {
                        const nfcPermission = await navigator.permissions.query({ name: 'nfc' });
                        console.log('NFC permission status:', nfcPermission.state);
                        
                        if (nfcPermission.state === 'denied') {
                            showError('NFC permission denied. Please enable NFC in your browser settings.');
                        }
                    } catch (e) {
                        console.log('Could not check NFC permission:', e);
                    }
                }
            } else {
                console.log('❌ Web NFC API not supported.');
                
                if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
                    showError('iOS does not support Web NFC. Consider using an Android device with Chrome.');
                } else if (!/Android/.test(navigator.userAgent)) {
                    showError('Web NFC requires Chrome on Android. Please use a compatible device.');
                } else {
                    showError('Web NFC not available. Make sure you are using Chrome and NFC is enabled.');
                }
            }
            
            // Load custom zones
            fetch('/get_custom_tags')
                .then(response => response.json())
                .then(data => {
                    if (data.tags) {
                        data.tags.forEach(tag => {
                            addTagToFloor(tag.id, tag.location, tag.floor);
                        });
                        totalZones += data.tags.length;
                        updateProgress();
                    }
                });
        });
        
        // Test read a single tag
        async function testReadTag() {
            if (!('NDEFReader' in window)) {
                showError('NFC not supported');
                return;
            }
            
            try {
                const ndef = new NDEFReader();
                await ndef.scan();
                
                showSuccess('📡 Hold an NFC tag near the device to read...');
                
                ndef.addEventListener('reading', event => {
                    const decoder = new TextDecoder();
                    let tagContent = '';
                    
                    for (const record of event.message.records) {
                        const data = decoder.decode(record.data);
                        tagContent += data + ' ';
                    }
                    
                    // Display what's on the tag
                    alert(`NFC Tag Content:\n${tagContent.trim()}\n\nType: ${event.message.records[0].recordType}`);
                    
                    // Check if it's one of our zones
                    const zoneMatch = tagContent.match(/10\d{6}/);
                    if (zoneMatch) {
                        showSuccess(`Zone tag detected: ${zoneMatch[0]}`);
                    }
                }, { once: true });
                
                ndef.addEventListener('readingerror', () => {
                    showError('Cannot read this NFC tag');
                }, { once: true });
                
            } catch (error) {
                showError('Read failed: ' + error.message);
            }
        }
        
        // Continuous read mode for quick scanning
        let continuousReadActive = false;
        async function startContinuousRead() {
            if (!('NDEFReader' in window)) {
                showError('NFC not supported');
                return;
            }
            
            if (continuousReadActive) {
                showError('Reading mode already active');
                return;
            }
            
            try {
                const ndef = new NDEFReader();
                await ndef.scan();
                continuousReadActive = true;
                
                showSuccess('📡 NFC Reading Mode Active - Tap any tag to read');
                
                ndef.addEventListener('reading', event => {
                    const decoder = new TextDecoder();
                    
                    for (const record of event.message.records) {
                        const data = decoder.decode(record.data).trim();
                        
                        // Check if it's a zone ID (8 digits starting with 10)
                        if (/^10\d{6}$/.test(data)) {
                            // Find the zone card
                            const card = document.getElementById('zone-' + data);
                            if (card && !card.classList.contains('visited')) {
                                const btn = card.querySelector('.write-btn');
                                const statusBadge = document.getElementById('status-' + data);
                                markAsVisited(data, card, btn, statusBadge);
                                
                                // Get location from the card
                                const locationText = card.querySelector('.zone-location').textContent;
                                showSuccess(`✅ Verified: ${data} - ${locationText}`);
                            } else if (card && card.classList.contains('visited')) {
                                showSuccess(`Tag ${data} already visited`);
                            } else {
                                showSuccess(`Tag read: ${data} (not in current tour)`);
                            }
                        }
                    }
                });
                
                ndef.addEventListener('readingerror', () => {
                    console.log('NFC read error - incompatible tag');
                });
                
            } catch (error) {
                continuousReadActive = false;
                showError('Failed to start reading mode: ' + error.message);
            }
        }

        // Handle keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeModal();
                closeAddTagModal();
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    # Calculate total zones properly
    total = sum(len(zones) for zones in zones_data.values())
    return render_template_string(HTML_TEMPLATE, zones_data=zones_data, total_zones=total)

@app.route('/mark_visited', methods=['POST'])
def mark_visited():
    data = request.get_json()
    zone_id = data.get('zoneId')
    if zone_id:
        visited_zones[zone_id] = {
            'timestamp': datetime.now().isoformat(),
            'visited': True
        }
    return jsonify({'success': True, 'zone_id': zone_id})

@app.route('/add_custom_tag', methods=['POST'])
def add_custom_tag():
    data = request.get_json()
    tag_id = data.get('id')
    location = data.get('location')
    floor = data.get('floor')
    
    if tag_id and location and floor:
        if floor not in custom_zones:
            custom_zones[floor] = []
        
        custom_zones[floor].append({
            'id': tag_id,
            'location': location,
            'visited': False
        })
        
        # Also add to main zones_data for persistence
        if floor in zones_data:
            zones_data[floor].append({
                'id': tag_id,
                'location': location,
                'visited': False
            })
        
        return jsonify({'success': True, 'tag': {'id': tag_id, 'location': location, 'floor': floor}})
    
    return jsonify({'success': False, 'error': 'Missing required fields'})

@app.route('/get_custom_tags')
def get_custom_tags():
    all_custom = []
    for floor, tags in custom_zones.items():
        for tag in tags:
            all_custom.append({
                'id': tag['id'],
                'location': tag['location'],
                'floor': floor
            })
    return jsonify({'tags': all_custom})

@app.route('/status')
def status():
    total = sum(len(zones) for zones in zones_data.values())
    visited = len(visited_zones)
    return jsonify({
        'total_zones': total,
        'visited_zones': visited,
        'progress': round((visited / total * 100), 2) if total > 0 else 0,
        'visited_list': list(visited_zones.keys())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
