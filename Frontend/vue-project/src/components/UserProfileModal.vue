<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  isOpen: Boolean,
  currentUser: Object
})

const emit = defineEmits(['close', 'save', 'upload-avatar'])

const editingProfile = ref({
    name: '',
    phone: '',
    birthDate: '',
    avatarUrl: ''
})

// При открытии окна копируем данные юзера в форму
watch(() => props.isOpen, (newVal) => {
    if (newVal) {
        editingProfile.value = {
            name: props.currentUser.name,
            phone: props.currentUser.phone,
            birthDate: props.currentUser.birthDate,
            avatarUrl: props.currentUser.avatar
        }
    }
})

const fileInput = ref(null)
const triggerUpload = () => fileInput.value.click()

const handleFile = (event) => {
    const file = event.target.files[0]
    if (file) emit('upload-avatar', file, editingProfile.value)
}

const save = () => {
    emit('save', editingProfile.value)
}
</script>

<template>
    <div v-if="isOpen" class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-content">
        <div class="modal-header">
            <h2>Настройки</h2>
            <button @click="$emit('close')" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <div class="settings-avatar">
             <img :src="editingProfile.avatarUrl" class="avatar-large" />
             <input type="file" ref="fileInput" @change="handleFile" style="display: none" accept="image/*" />
             <button @click="triggerUpload" class="upload-btn">Изменить фото</button> 
          </div>
          <div class="settings-form">
              <label>Имя пользователя</label><input type="text" v-model="editingProfile.name" /> 
              <label>Номер телефона</label><input type="tel" v-model="editingProfile.phone" />
              <label>Дата рождения</label><input type="date" v-model="editingProfile.birthDate" />
              <button @click="save" class="save-btn">Сохранить</button>
          </div>
        </div>
      </div>
    </div>
</template>

<style scoped>
.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.7); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal-content { background: #1e293b; width: 400px; border-radius: 12px; padding: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1); }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; }
.close-btn { background: none; border: none; color: #94a3b8; font-size: 24px; cursor: pointer; }
.close-btn:hover { color: white; }
.settings-avatar { display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 20px; }
.avatar-large { width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid #06b6d4; }
.upload-btn { background: #0f172a; border: 1px solid #06b6d4; color: #06b6d4; padding: 5px 15px; border-radius: 20px; cursor: pointer; font-size: 0.9em; }
.settings-form label { display: block; margin-bottom: 5px; color: #94a3b8; font-size: 0.9em; }
.settings-form input { width: 100%; padding: 10px; margin-bottom: 15px; background: #0f172a; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: white; outline: none;}
.save-btn { width: 100%; padding: 10px; background: #06b6d4; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; margin-top: 10px; }
.save-btn:hover { background: #0891b2; }
</style>
