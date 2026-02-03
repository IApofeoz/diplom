<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  src: String
})

const audioRef = ref(null)
const isPlaying = ref(false)
const duration = ref(0)
const currentTime = ref(0)

const togglePlay = () => {
  if (!audioRef.value) return
  
  if (isPlaying.value) {
    audioRef.value.pause()
  } else {
    // Останавливаем все остальные аудио на странице (опционально)
    document.querySelectorAll('audio').forEach(el => {
        if(el !== audioRef.value) el.pause()
    })
    audioRef.value.play()
  }
  isPlaying.value = !isPlaying.value
}

const onTimeUpdate = () => {
  if (audioRef.value) currentTime.value = audioRef.value.currentTime
}

const onLoadedMetadata = () => {
  if (audioRef.value) duration.value = audioRef.value.duration
}

const onEnded = () => {
  isPlaying.value = false
  currentTime.value = 0
}

const seek = (event) => {
  const time = event.target.value
  if (audioRef.value) {
      audioRef.value.currentTime = time
      currentTime.value = time
  }
}

const formatTime = (seconds) => {
  if (!seconds || isNaN(seconds)) return "0:00"
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s < 10 ? '0' : ''}${s}`
}
</script>

<template>
  <div class="custom-player">
    <button class="play-btn" @click="togglePlay">
      <i :class="isPlaying ? 'fas fa-pause' : 'fas fa-play'"></i>
    </button>
    
    <div class="progress-container">
        <input 
            type="range" 
            min="0" 
            :max="duration" 
            :value="currentTime" 
            @input="seek"
            class="seek-bar"
        />
    </div>
    
    <span class="time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
    
    <!-- Скрытый нативный аудио элемент -->
    <audio 
        ref="audioRef" 
        :src="src" 
        @timeupdate="onTimeUpdate" 
        @loadedmetadata="onLoadedMetadata"
        @ended="onEnded"
        style="display: none;"
    ></audio>
  </div>
</template>

<style scoped>
.custom-player {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(0, 0, 0, 0.2); /* Темная подложка */
    padding: 8px 12px;
    border-radius: 20px;
    width: 240px; /* Фиксированная ширина */
    margin-top: 5px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.play-btn {
    background: #06b6d4;
    border: none;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 12px;
    transition: transform 0.1s;
    flex-shrink: 0;
}
.play-btn:active { transform: scale(0.9); }

.progress-container { flex: 1; display: flex; align-items: center; }

.seek-bar {
    -webkit-appearance: none;
    width: 100%;
    height: 4px;
    background: rgba(255, 255, 255, 0.3);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
}

/* Ползунок (Thumb) для Chrome/Safari */
.seek-bar::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 12px;
    height: 12px;
    background: white;
    border-radius: 50%;
    cursor: pointer;
    transition: 0.2s;
}
.seek-bar::-webkit-slider-thumb:hover { transform: scale(1.2); }

.time {
    font-size: 11px;
    color: #cbd5e1;
    font-family: monospace;
    min-width: 60px;
    text-align: right;
}
</style>
