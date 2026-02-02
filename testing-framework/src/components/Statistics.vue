
<script setup lang="ts">
defineProps<{
  stats: {
    connected: boolean;
    inferenceTime: number;
    fps: number;
    accuracy: number;
    totalRuns: number;
    personDetected: boolean | null;
    currentImage: string;
  }
}>();

const emit = defineEmits(['start-test', 'stop-test', 'next-image']);

</script>

<template>
  <div class="stats-panel">
    <h2>TinyML Tester</h2>
    
    <div class="metric-group">
        <div class="status-indicator" :class="{ connected: stats.connected }">
            {{ stats.connected ? 'Connected' : 'Disconnected' }}
        </div>
    </div>

    <div class="metrics-grid">
        <div class="card" title="Frames Per Second (Inference Rate)">
            <h3>FPS</h3>
            <div class="value">{{ stats.fps.toFixed(1) }}</div>
        </div>
        <div class="card" title="On-Device Inference Time (Processing time)">
            <h3>Latency</h3>
            <div class="value">{{ stats.inferenceTime }} ms</div>
        </div>
        <div class="card" title="Percentage of correct predictions based on dataset labels">
            <h3>Accuracy</h3>
            <div class="value">{{ (stats.accuracy * 100).toFixed(1) }}%</div>
        </div>
        <div class="card" title="Total number of inference predictions received">
            <h3>Inferences</h3>
            <div class="value">{{ stats.totalRuns }}</div>
        </div>
    </div>

    <div class="current-state" v-if="stats.currentImage">
        <p><strong>Image:</strong> {{ stats.currentImage }}</p>
        <p><strong>Prediction:</strong> {{ stats.personDetected === null ? '...' : (stats.personDetected ? 'Person' : 'No Person') }}</p>
    </div>

    <div class="controls">
        <button @click="emit('start-test')">Next Image</button>
        <!-- Add more controls as needed -->
    </div>
  </div>
</template>

<style scoped>
/* ... */
.stats-panel {
    background: #1e1e1e;
    color: #e0e0e0;
    padding: 1.5rem; 
    /* removed padding-left:0 since it's now full width and looks better with some padding */
    height: 100%;
    overflow-y: auto;
    /* border-right removed, handled by border-top in parents CSS */
    display: flex;
    flex-direction: column;
}

h2 {
    margin-bottom: 1.5rem;
    color: #42b983;
}

.status-indicator {
    padding: 0.5rem;
    background: #ff5252;
    color: white;
    text-align: center;
    border-radius: 4px;
    margin-bottom: 1rem;
    font-weight: bold;
    display: inline-block; /* Don't take full width if not needed */
    min-width: 150px;
}

.status-indicator.connected {
    background: #4caf50;
}

/* Horizontal Grid for Bottom Region */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr); /* 4 Columns */
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.card {
    background: #2c2c2c;
    padding: 1.5rem;
    border-radius: 8px;
    text-align: left;
}

/* ... rest ... */

.card h3 {
    font-size: 0.8rem;
    text-transform: uppercase;
    color: #888;
    margin-bottom: 0.5rem;
}

.card .value {
    font-size: 1.5rem;
    font-weight: 500;
}

.controls button {
    width: 100%;
    padding: 1rem;
    background: #42b983;
    border: none;
    color: white;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    transition: background 0.2s;
}

.controls button:hover {
    background: #3aa876;
}
</style>
