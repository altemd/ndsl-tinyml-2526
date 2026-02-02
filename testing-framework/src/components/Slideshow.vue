
<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue';

const props = defineProps<{
  imageUrl: string | null;
  position: { x: number; y: number };
  size: { width: number; height: number };
  locked: boolean;
}>();

const emit = defineEmits(['start-drag', 'update:size']);
const containerRef = ref<HTMLElement | null>(null);
let resizeObserver: ResizeObserver | null = null;

const style = computed(() => ({
    top: `${props.position.y}px`,
    left: `${props.position.x}px`,
    width: `${props.size.width}px`,
    height: `${props.size.height}px`,
    position: 'absolute' as const,
    pointerEvents: props.locked ? 'none' as const : 'auto' as const
}));

function onMouseDown(e: MouseEvent) {
    if (props.locked) return;
    emit('start-drag', e);
}

onMounted(() => {
    if (containerRef.value) {
        resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                // We only care about explicit user resizing, which changes the element's style or content rect.
                // However, ResizeObserver fires initially too. We should debounce or check diff.
                const { width, height } = entry.contentRect;
                // contentRect doesn't include borders etc.
                // clientWidth/clientHeight might be safer for consistent sizing if we use box-sizing: border-box
                const el = entry.target as HTMLElement;
                const newW = el.offsetWidth; // Includes border
                const newH = el.offsetHeight;

                if (newW !== props.size.width || newH !== props.size.height) {
                    emit('update:size', { width: newW, height: newH });
                }
            }
        });
        resizeObserver.observe(containerRef.value);
    }
});

onUnmounted(() => {
    if (resizeObserver) resizeObserver.disconnect();
});
</script>

<template>
  <div class="slideshow-container" ref="containerRef" :style="style" :class="{ locked: locked }">
    <!-- Drag Handle (Always rendered to preserve space, hidden when locked) -->
    <div class="drag-handle" @mousedown="onMouseDown" :class="{ hidden: locked }">
        <span>⋮⋮ Drag</span>
    </div>

    <div v-if="imageUrl" class="image-wrapper">
        <img :src="imageUrl" alt="Test Image" class="slideshow-image" draggable="false" />
    </div>
    <div v-else class="placeholder">
        <p>No Image Loaded</p>
    </div>
  </div>
</template>

<style scoped>
.slideshow-container {
    /* width/height controlled by style prop now */
    background: #000;
    border: 2px solid #333;
    box-sizing: border-box; /* CRITICAL: Prevent infinite loop with offsetWidth */
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    z-index: 3000; 
    user-select: none;
    display: flex;
    flex-direction: column;
    
    /* Resizable */
    resize: both;
    overflow: hidden;
    min-width: 150px;
    min-height: 150px;
}

.slideshow-container.locked {
    resize: none;
    border-color: #ff5252; /* Visual indicator of lock */
}

.drag-handle {
    height: 24px;
    background: #333;
    cursor: move;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #888;
    font-size: 0.8rem;
    flex-shrink: 0;
    transition: background 0.2s, opacity 0.2s;
}

.drag-handle.hidden {
    opacity: 0;
    pointer-events: none;
    cursor: default;
    background: transparent; /* Optional: hide background if desired, but keeping space is key */
}

.drag-handle:not(.hidden):hover {
    background: #444;
    color: white;
}

.image-wrapper {
    flex: 1;
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    background: white;
    overflow: hidden;
    pointer-events: none; /* Let clicks pass through if needed, but mainly stops dragging image itself */
}

.slideshow-image {
    width: 100%;
    height: 100%;
    object-fit: contain; /* Maintain aspect ratio */
    display: block;
}

.placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    text-align: center;
}
</style>
