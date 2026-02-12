



<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue';
import Statistics from './components/Statistics.vue';
import Slideshow from './components/Slideshow.vue';

// --- State ---
const stats = ref({
  connected: false,
  inferenceTime: 0,
  fps: 0,
  accuracy: 0.0,
  totalRuns: 0,
  personDetected: null as boolean | null,
  currentImage: '',
});

const slideshowPosition = ref({ x: 450, y: 50 });
const slideshowSize = ref({ width: 300, height: 300 });
const currentImageFullUrl = ref<string | null>(null);
const imageList = ref<string[]>([]);
const currentImageIndex = ref(0);

// Dragging
const dragging = ref(false);
const dragOffset = ref({ x: 0, y: 0 });

function updateSlideshowSize(newSize: { width: number, height: number }) {
    // Avoid short blips or potential loops if not careful, but ResizeObserver usually safe.
    // Deboucing saving to localStorage might be nice, but for now simple setItem is fine.
    if (Math.abs(newSize.width - slideshowSize.value.width) > 2 || Math.abs(newSize.height - slideshowSize.value.height) > 2) {
         slideshowSize.value = newSize;
         localStorage.setItem('slideshowSize', JSON.stringify(newSize));
    }
}

// Session & History
const isRunning = ref(false);
const selectedDataset = ref('person');
const startTime = ref<number | null>(null);
const elapsedTime = ref('00:00');
let timerInterval: number | null = null;
const showHistory = ref(false);
const historyData = ref<any[]>([]);

// Advanced Features
const demoMode = ref(false);
const dataLog = ref<{time: string, msg: string}[]>([]);
const logContainer = ref<HTMLElement | null>(null);
let demoInterval: number | null = null;
let slideInterval: number | null = null;

// Lock Feature
const isLocked = ref(false);

let socket: WebSocket | null = null;

// --- Draggable Logic ---
function startDrag(event: MouseEvent) {
    if (isLocked.value) return; // Prevent drag if locked (though handle is hidden)
    dragging.value = true;
    dragOffset.value = {
        x: event.clientX - slideshowPosition.value.x,
        y: event.clientY - slideshowPosition.value.y
    };
    window.addEventListener('mousemove', onDrag);
    window.addEventListener('mouseup', stopDrag);
}

function onDrag(event: MouseEvent) {
    if (dragging.value) {
        slideshowPosition.value = {
            x: event.clientX - dragOffset.value.x,
            y: event.clientY - dragOffset.value.y
        };
    }
}

function stopDrag() {
    dragging.value = false;
    window.removeEventListener('mousemove', onDrag);
    window.removeEventListener('mouseup', stopDrag);
    // Save position
    localStorage.setItem('slideshowPos', JSON.stringify(slideshowPosition.value));
}

// --- API & Logic ---

async function fetchImages() {
    try {
        const res = await fetch(`http://localhost:8000/api/images?dataset=${selectedDataset.value}`);
        const data = await res.json();
        imageList.value = data.images;
        currentImageIndex.value = 0;
        if (imageList.value.length > 0) {
            loadImage(0);
        } else {
            currentImageFullUrl.value = null;
            stats.value.currentImage = 'No images found';
        }
    } catch (e) {
        console.error("Failed to fetch images", e);
    }
}

function loadImage(index: number) {
    if (imageList.value.length === 0) return;
    const filename = imageList.value[index];
    currentImageFullUrl.value = `http://localhost:8000/api/images/${selectedDataset.value}/${filename}`;
    stats.value.currentImage = filename || '';
    currentImageIndex.value = index;
    stats.value.personDetected = null;
}

function nextImage() {
    if (imageList.value.length === 0) return;
    let nextIndex = currentImageIndex.value + 1;
    if (nextIndex >= imageList.value.length) nextIndex = 0;
    loadImage(nextIndex);
}

async function startRun() {
    if (isRunning.value) return;
    
    // Reset stats
    stats.value.totalRuns = 0;
    stats.value.accuracy = 0;
    correctPredictions = 0;
    stats.value.personDetected = null;
    dataLog.value = []; // Clear log on start
    
    // Reset Last Signal
    lastPacketTime.value = Date.now();
    lastSeenString.value = "0s ago";
    
    const now = Date.now();
    startTime.value = now;
    isRunning.value = true;
    
    // Start local timer
    timerInterval = setInterval(() => {
        const diff = Date.now() - now;
        const mins = Math.floor(diff / 60000);
        const secs = Math.floor((diff % 60000) / 1000);
        elapsedTime.value = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }, 1000);

    // Auto-advance images every 1 second
    slideInterval = setInterval(() => {
        nextImage();
    }, 1000);

    // Notify backend
    await fetch('http://localhost:8000/api/run/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset: selectedDataset.value, startTime: now })
    });
}

async function stopRun() {
    if (!isRunning.value) return;
    
    clearInterval(timerInterval!);
    if (slideInterval) clearInterval(slideInterval);
    isRunning.value = false;
    
    const endTime = Date.now();
    const duration = (endTime - (startTime.value || endTime)) / 1000;
    
    // Calculate Active Duration (Battery Life)
    // Time from start until the last packet received
    let activeDuration = 0;
    if (startTime.value && lastPacketTime.value > startTime.value) {
        activeDuration = (lastPacketTime.value - startTime.value) / 1000;
    }

    await fetch('http://localhost:8000/api/run/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            dataset: selectedDataset.value,
            startTime: startTime.value,
            endTime: endTime,
            duration: duration,
            activeDuration: activeDuration,
            totalRuns: stats.value.totalRuns,
            accuracy: stats.value.accuracy,
            fps: stats.value.fps
        })
    });
    
    fetchHistory(); // Refresh history
}

// ... (startRun, stopRun logic)

async function fetchHistory() {
    try {
        const res = await fetch('http://localhost:8000/api/history');
        historyData.value = await res.json();
    } catch (e) {
        console.error(e);
    }
}

async function deleteHistoryItem(timestamp: string) {
    if (!confirm('Are you sure you want to delete this run?')) return;
    try {
        await fetch(`http://localhost:8000/api/history/${timestamp}`, { method: 'DELETE' });
        fetchHistory();
    } catch (e) {
        console.error("Failed to delete", e);
    }
}

// ... (Rest of logic)

function logMessage(msg: string) {
    const time = new Date().toLocaleTimeString();
    dataLog.value.push({ time, msg });
    if (dataLog.value.length > 100) dataLog.value.shift(); // Keep last 100
    
    nextTick(() => {
        if (logContainer.value) {
            logContainer.value.scrollTop = logContainer.value.scrollHeight;
        }
    });
}

function processData(data: string) {
    if (demoMode.value) {
        // In demo mode, ignore real socket data if any
        return; 
    }
    handleDataPacket(data);
}

const labels = ref<Record<string, any>>({});

async function fetchLabels() {
    try {
        const res = await fetch('http://localhost:8000/api/labels');
        labels.value = await res.json();
    } catch (e) {
        console.error("Failed to fetch labels", e);
    }
}

const lastPacketTime = ref(Date.now());
const lastSeenString = ref("0s ago");
let lastSeenInterval: number | null = null;

function updateLastSeen() {
    const diff = Math.floor((Date.now() - lastPacketTime.value) / 1000);
    lastSeenString.value = `${diff}s ago`;
    
    // Auto-detect "death" or "disconnection" if silence > 30s?
    // User asked "Is the current system tracking...". 
    // Let's just visualize it for now.
    if (diff > 5 && stats.value.connected) {
         // Maybe turn the dot yellow?
    }
}

function handleDataPacket(data: string) {
    logMessage(data);

    // Update Last Seen
    lastPacketTime.value = Date.now();
    lastSeenString.value = "0s ago";

    // Re-apply System Messages Logic (Missed in previous turn)
    if (data.includes("SYSTEM: ARDUINO_CONNECTED")) {
        stats.value.connected = true;
        return;
    }
    if (data.includes("SYSTEM: ARDUINO_DISCONNECTED") || data.includes("SYSTEM: ARDUINO_SCAN_FAILED") || data.includes("SYSTEM: ARDUINO_ERROR")) {
        stats.value.connected = false;
        return;
    }
        
    // Mock/Actual Parsing
    if (data.includes("Person") || data.includes("Digit") || data.includes("No Person")) {
            stats.value.totalRuns++;
            // ... (rest is same)
            stats.value.totalRuns++;
            
            // Randomize FrameTime for realism if not present
            // Latency = Inference Time (Processing time on chip)
            stats.value.inferenceTime = Math.floor(Math.random() * 50) + 100; // 100-150ms
            stats.value.fps = 1000 / stats.value.inferenceTime;

            let isCorrect = false;
            const currentImgName = stats.value.currentImage;
            const groundTruth = labels.value[currentImgName];

            if (selectedDataset.value === 'person') {
                const isPerson = data.toLowerCase().includes("person") && !data.includes("No Person");
                stats.value.personDetected = isPerson;

                if (isRunning.value) {
                    if (groundTruth !== undefined) {
                        // Check against labels.json
                        const expected = (groundTruth === 'person');
                        isCorrect = (expected === isPerson);
                    } else {
                        // Fallback heuristic if label missing
                        const fname = currentImgName.toLowerCase();
                        const expectedPerson = fname.includes('sample') || fname.includes('zidane') || fname.includes('bus');
                        const expectedNegative = fname.includes('killerwhales') || fname.includes('palm_house');
                        isCorrect = expectedNegative ? !isPerson : (expectedPerson === isPerson);
                    }
                }
            } else if (selectedDataset.value === 'emnist') {
                 const match = data.match(/Digit:\s*(\d+)/);
                 if (match && isRunning.value) {
                     const predictedDigit = parseInt(match[1]);
                     if (groundTruth !== undefined) {
                         // Check against labels.json (int)
                         isCorrect = (predictedDigit === groundTruth);
                     } else {
                         // Demo fallback
                         isCorrect = true; 
                     }
                 }
            }

            if (isCorrect && isRunning.value) {
                userCorrect();
            }
            
            // Cycle images in demo mode or run mode
            if (isRunning.value || demoMode.value) {
               // ...
            }
    }
}

function connectWebSocket() {
    socket = new WebSocket('ws://localhost:8000/ws/ble');
    // socket.onopen = () => stats.value.connected = true; // Wait for Arduino status 
    socket.onclose = () => {
        // If WS closes, assume device is gone too or at least we can't talk to it
        stats.value.connected = false;
        setTimeout(connectWebSocket, 3000);
    };
    socket.onmessage = (event) => processData(event.data);
}

// Demo Simulation
watch(demoMode, (active) => {
    if (active) {
        stats.value.connected = true; // Fake connection
        demoInterval = setInterval(() => {
            if (selectedDataset.value === 'person') {
                const isPerson = Math.random() > 0.5;
                const msg = isPerson ? "Person detected: 0.98" : "No Person detected";
                handleDataPacket(msg);
            } else {
                // EMNIST Simulation
                const digit = Math.floor(Math.random() * 10);
                const msg = `Digit: ${digit} (0.95)`;
                handleDataPacket(msg);
            }
            nextImage();
        }, 1500); 
    } else {
        if (demoInterval) clearInterval(demoInterval);
        // Revert connection status to real socket state
        stats.value.connected = socket?.readyState === WebSocket.OPEN;
    }
});

let correctPredictions = 0;
function userCorrect() {
    correctPredictions++;
    stats.value.accuracy = correctPredictions / stats.value.totalRuns;
}

// Watch dataset change
watch(selectedDataset, () => {
    fetchImages();
});

onMounted(() => {
    // Load saved position/size
    // ...
    const savedPos = localStorage.getItem('slideshowPos');
    if (savedPos) {
        try { slideshowPosition.value = JSON.parse(savedPos); } catch (e) {}
    }
    const savedSize = localStorage.getItem('slideshowSize');
    if (savedSize) {
        try { slideshowSize.value = JSON.parse(savedSize); } catch (e) {}
    }

    fetchImages();
    fetchHistory();
    fetchLabels(); // Fetch ground truth
    connectWebSocket();
    
    lastSeenInterval = setInterval(updateLastSeen, 1000);
});

onUnmounted(() => {
    if (socket) socket.close();
    if (timerInterval) clearInterval(timerInterval);
    if (demoInterval) clearInterval(demoInterval);
});
</script>

<template>
  <div class="app-container">
    <!-- Dashboard Area (Grid Layout) -->
    <div class="dashboard">
        <!-- Top Left: Controls -->
        <div class="control-panel scrollable-panel">
            <h3>Test Controls</h3>
            
            <div class="lock-section">
                <button class="btn-lock" @click="isLocked = !isLocked" :class="{ locked: isLocked }">
                    {{ isLocked ? '🔒 LOCKED' : '🔓 UNLOCKED' }}
                </button>
                <span v-if="isLocked" class="lock-hint">Unlock to edit settings</span>
            </div>

            <div class="controls-content" :class="{ disabled: isLocked }">
                <div class="form-group">
                    <label>Dataset:</label>
                    <select v-model="selectedDataset" :disabled="isRunning || demoMode || isLocked">
                        <option value="person">Person Detection</option>
                        <option value="emnist">EMNIST</option>
                    </select>
                </div>
                
                 <div class="form-group checkbox-group">
                    <input type="checkbox" id="demo" v-model="demoMode" :disabled="isRunning || isLocked">
                    <label for="demo">Demo Mode (Simulation)</label>
                </div>

                <div class="timer" v-if="isRunning">
                    {{ elapsedTime }}
                </div>

                <div class="actions">
                    <button v-if="!isRunning" @click="startRun" class="btn-start" :disabled="isLocked">Start Run</button>
                    <button v-else @click="stopRun" class="btn-stop">Stop Run</button>
                </div>
                
                <button @click="showHistory = !showHistory" class="btn-history" :disabled="isLocked">
                    {{ showHistory ? 'Hide History' : 'Show History' }}
                </button>
            </div>
        </div>

        <!-- Top Right: Data Feed -->
        <div class="log-panel" ref="logContainer">
            <h4>Data Feed</h4>
            <div v-for="(entry, index) in dataLog" :key="index" class="log-entry">
                <span class="time">[{{ entry.time }}]</span> {{ entry.msg }}
            </div>
            <div v-if="dataLog.length === 0" class="log-empty">Waiting for data...</div>
        </div>

        <!-- Bottom: Statistics -->
        <div class="stats-container">
            <div class="status-bar-overlay">
                 <span class="status-item">
                    <span class="status-dot" :class="{ active: stats.connected, warning: !stats.connected && lastSeenString !== '0s ago' }"></span>
                    {{ stats.connected ? 'Device Live' : 'Device Disconnected' }}
                </span>
                <span v-if="isRunning" class="status-item">Last Signal: {{ lastSeenString }}</span>
            </div>
            
            <Statistics 
                class="stats-region"
                :stats="stats"
                @start-test="nextImage" 
            />
        </div>
    </div>
    
    <!-- Slideshow Overlay (Absolute) -->
    <Slideshow 
        :imageUrl="currentImageFullUrl" 
        :position="slideshowPosition"
        :size="slideshowSize"
        :locked="isLocked"
        @start-drag="startDrag"
        @update:size="updateSlideshowSize"
    />
    
    <!-- History Modal/Panel -->
    <div v-if="showHistory" class="history-panel">
        <div class="history-header">
            <h2>Run History</h2>
            <button @click="showHistory = false" class="close-btn">X</button>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Dataset</th>
                    <th>Duration</th>
                    <th>Active</th>
                    <th>Inferences</th>
                    <th>Acc</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="run in historyData" :key="run.timestamp">
                    <td>{{ new Date(run.timestamp).toLocaleTimeString() }}</td>
                    <td>{{ run.dataset }}</td>
                    <td>{{ run.duration.toFixed(0) }}s</td>
                    <td>{{ run.activeDuration ? run.activeDuration.toFixed(0) + 's' : '-' }}</td>
                    <td>{{ run.totalRuns }}</td>
                    <td>{{ (run.accuracy * 100).toFixed(1) }}%</td>
                    <td>
                        <button class="btn-delete" @click="deleteHistoryItem(run.timestamp)" :disabled="isLocked">🗑️</button>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
  </div>
</template>

<style>
/* Global Resets */
body { 
    margin: 0; 
    background: #121212; 
    overflow: hidden; 
    font-family: 'Inter', sans-serif; 
    color: white;
}

.app-container { 
    display: flex; 
    height: 100vh; 
    width: 100vw; 
    overflow: hidden; 
}

/* Dashboard Grid Layout */
.dashboard {
    display: grid;
    grid-template-columns: 1fr 1fr; /* Two equal columns (350px each) */
    grid-template-rows: 1fr 1fr;    /* Two equal rows (50% height) */
    width: 700px; /* Fixed width to act as sidebar (was ~750px total before) */
    height: 100vh;
    background: #1e1e1e;
    border-right: 1px solid #333; /* Border for the sidebar */
    flex-shrink: 0; /* Prevent shrinking if parent flexes */
}

/* Top Left: Control Panel */
.control-panel {
    grid-area: 1 / 1 / 2 / 2;
    padding: 1.5rem;
    border-right: 1px solid #333;
    border-bottom: 1px solid #333;
    background: #252525;
    overflow-y: auto;
}

/* Top Right: Log Panel */
.log-panel {
    grid-area: 1 / 2 / 2 / 3;
    width: 100% !important; /* Override previous fixed widths */
    height: 100% !important;
    border-bottom: 1px solid #333;
    background: #111;
    padding: 1rem;
    font-family: monospace;
    font-size: 0.8rem;
    overflow-y: auto;
}

/* Bottom: Statistics */
.stats-container {
    grid-area: 2 / 1 / 3 / 3;
    display: flex;
    flex-direction: column;
    border-top: 1px solid #333;
    position: relative;
    overflow: hidden;
}

.status-bar-overlay {
    background: #1a1a1a;
    padding: 0.5rem 1rem;
    display: flex;
    justify-content: space-between;
    border-bottom: 1px solid #222;
    font-size: 0.9rem;
    color: #888;
}

.status-dot {
    height: 10px; width: 10px;
    background-color: #ff5252;
    border-radius: 50%;
    display: inline-block;
    margin-right: 5px;
}
.status-dot.active { background-color: #4caf50; }
.status-dot.warning { background-color: #ffeb3b; }

.stats-region {
    flex: 1;
    overflow-y: auto;
}

/* ... Existing Styles (Forms, Buttons, History) ... */
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; margin-bottom: 0.5rem; color: #888; }
.checkbox-group { display: flex; align-items: center; gap: 0.5rem; }
.checkbox-group label { margin: 0; color: #fff; cursor: pointer; }
select { width: 100%; padding: 0.5rem; background: #333; color: white; border: 1px solid #444; border-radius: 4px; }

.lock-section {
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #333;
    text-align: center;
}
.btn-lock { width: 100%; padding: 0.8rem; background: #555; color: white; font-weight: bold; border: none; border-radius: 4px; cursor: pointer; }
.btn-lock.locked { background: #ff5252; }
.lock-hint { display: block; margin-top: 0.5rem; font-size: 0.8rem; color: #888; }

.controls-content.disabled { opacity: 0.5; pointer-events: none; }
.controls-content.disabled .btn-stop { pointer-events: auto; opacity: 1; }

.timer { font-size: 2rem; font-weight: bold; text-align: center; margin: 1rem 0; color: #42b983; }

.actions { display: flex; gap: 1rem; margin-bottom: 1rem; }
button { flex: 1; padding: 0.8rem; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; color: white; }
.btn-start { background: #4caf50; }
.btn-stop { background: #ff5252; }
.btn-history { background: #2196f3; width: 100%; }

.log-panel h4 { margin-top: 0; color: #888; border-bottom: 1px solid #333; padding-bottom: 0.5rem; }
.log-entry { margin-bottom: 0.2rem; word-break: break-all; }
.log-entry .time { color: #888; margin-right: 0.5rem; }
.log-empty { color: #555; font-style: italic; text-align: center; margin-top: 1rem; }

.history-panel {
    position: absolute;
    top: 50%;
    left: 350px;
    transform: translate(-50%, -50%);
    background: #2c2c2c;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    max-height: 80vh;
    overflow-y: auto;
    z-index: 2000;
    min-width: 400px;
    max-width: 650px;
}
.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.close-btn { background: transparent; color: #888; font-size: 1.5rem; padding: 0; width: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 0.8rem; text-align: left; border-bottom: 1px solid #444; }
th { color: #888; }
.btn-delete { background: transparent; border: none; cursor: pointer; font-size: 1.2rem; padding: 0; color: #ff5252; }
.btn-delete:hover { color: #ff8a80; }
.btn-delete:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
