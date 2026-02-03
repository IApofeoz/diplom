<script setup>
import { computed } from 'vue'

const props = defineProps({
  isOpen: Boolean,
  contact: Object // Данные собеседника
})

const emit = defineEmits(['close'])

// Форматируем дату рождения, если она есть
const formattedDate = computed(() => {
    if (!props.contact?.birthDate) return 'Не указана'
    return new Date(props.contact.birthDate).toLocaleDateString()
})
</script>

<template>
    <div v-if="isOpen && contact" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-content">
        <div class="modal-header">
            <h2>Информация</h2>
            <button @click="$emit('close')" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <div class="profile-avatar">
             <img :src="contact.avatar" class="avatar-large" />
             <div class="status-badge" :class="contact.status">
                 {{ contact.status === 'online' ? 'В сети' : 'Не в сети' }}
             </div>
          </div>
          
          <div class="info-list">
              <div class="info-item">
                  <label>Имя пользователя</label>
                  <p>{{ contact.name }}</p>
              </div>
              <div class="info-item">
                  <label>Номер телефона</label>
                  <p>{{ contact.phone || 'Не указан' }}</p>
              </div>
              <div class="info-item">
                  <label>Дата рождения</label>
                  <p>{{ formattedDate }}</p>
              </div>
          </div>
          
          <button @click="$emit('close')" class="action-btn">Закрыть</button>
        </div>
      </div>
    </div>
</template>

<style scoped>
.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.7); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal-content { background: #1e293b; width: 350px; border-radius: 12px; padding: 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1); }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.close-btn { background: none; border: none; color: #94a3b8; font-size: 24px; cursor: pointer; }
.close-btn:hover { color: white; }

.profile-avatar { display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 25px; position: relative; }
.avatar-large { width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 4px solid #0f172a; box-shadow: 0 0 0 2px #06b6d4; }

.status-badge { padding: 4px 12px; border-radius: 15px; font-size: 12px; font-weight: bold; margin-top: -15px; z-index: 2; background: #0f172a; border: 1px solid rgba(255,255,255,0.1); }
.status-badge.online { color: #10b981; border-color: #10b981; }
.status-badge.offline { color: #94a3b8; }

.info-list { display: flex; flex-direction: column; gap: 15px; }
.info-item label { font-size: 12px; color: #64748b; display: block; margin-bottom: 2px; }
.info-item p { font-size: 16px; color: #f1f5f9; font-weight: 500; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 5px; }

.action-btn { width: 100%; padding: 12px; background: rgba(255,255,255,0.05); color: white; border: none; border-radius: 8px; cursor: pointer; margin-top: 20px; transition: 0.2s; }
.action-btn:hover { background: rgba(255,255,255,0.1); }
</style>
