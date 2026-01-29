<script setup>
import { ref, computed, nextTick, onMounted, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

// --- НАСТРОЙКА API ---
const BASE_URL = 'http://localhost:8000' 

const api = axios.create({
  baseURL: BASE_URL,
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// --- СОСТОЯНИЕ (STATE) ---
const currentUser = ref({ 
    id: null, 
    name: 'Загрузка...', 
    avatar: '', 
    phone: '', 
    birthDate: '' 
})

// Временное состояние для формы настроек (чтобы не менять currentUser мгновенно)
const editingProfile = ref({
    name: '',
    phone: '',
    birthDate: ''
})

const contacts = ref([])
const messages = ref({}) 
const activeChatId = ref(null)
const newMessage = ref('')
const messagesContainer = ref(null)
const isSettingsOpen = ref(false)
let socket = null

// --- COMPUTED ---
const activeContact = computed(() => {
  if (!activeChatId.value) return null
  return contacts.value.find(c => c.id === activeChatId.value) || { 
    name: 'Загрузка...', 
    avatar: '', 
    status: 'offline' 
  }
})

const currentMessages = computed(() => {
  return activeChatId.value ? (messages.value[activeChatId.value] || []) : []
})

// --- WATCHERS ---
watch(currentMessages, async () => {
  await nextTick()
  scrollToBottom()
}, { deep: true })

// --- WEBSOCKET ---
const connectWebSocket = () => {
  const token = localStorage.getItem('access_token')
  if (!token) return

  const wsUrl = BASE_URL.replace('http', 'ws') + `/ws?token=${token}`
  socket = new WebSocket(wsUrl)

  socket.onopen = () => console.log("WS Connected")

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.type === 'status_update') {
        const contact = contacts.value.find(c => c.id === data.user_id)
        if (contact) contact.status = data.status
        return
    }

    if (data.type === 'messages_read') {
        const partnerId = data.user_id
        if (messages.value[partnerId]) {
            messages.value[partnerId].forEach(msg => {
                if (msg.senderId === currentUser.value.id) msg.isRead = true
            })
        }
        return
    }

    const partnerId = data.sender_id === currentUser.value.id ? data.recipient_id : data.sender_id
    
    if (!messages.value[partnerId]) messages.value[partnerId] = []

    const exists = messages.value[partnerId].find(m => m.id === data.id)
    if (!exists) {
      messages.value[partnerId].push({
        id: data.id,
        senderId: data.sender_id,
        text: data.content,
        time: new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isRead: data.is_read || false
      })
    }

    const contact = contacts.value.find(c => c.id === partnerId)
    if (contact) {
      contact.lastMessage = data.content
      contact.time = new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    if (activeChatId.value === partnerId && data.sender_id !== currentUser.value.id) {
        markAsRead(partnerId)
    }
  }

  socket.onclose = (e) => {
    console.log('WS Closed', e)
    setTimeout(() => {
        if (localStorage.getItem('access_token')) connectWebSocket()
    }, 3000)
  }
}

const markAsRead = (senderId) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "read_messages", sender_id: senderId }))
    }
}

// --- ФУНКЦИЯ СОХРАНЕНИЯ ПРОФИЛЯ ---
const saveProfile = async () => {
    // 1. Подготавливаем текущие и новые значения для сравнения (убираем лишние пробелы)
    const currentName = (currentUser.value.name || '').trim()
    const newName = (editingProfile.value.name || '').trim()
    
    const currentPhone = (currentUser.value.phone || '').trim()
    const newPhone = (editingProfile.value.phone || '').trim()
    
    // Для даты приводим пустые строки к null, чтобы корректно сравнивать
    const currentDate = currentUser.value.birthDate || null
    const newDate = editingProfile.value.birthDate || null

    // 2. Формируем объект только с измененными полями
    const payload = {}
    
    if (newName !== currentName && newName.length > 0) {
        payload.username = newName
    }
    
    if (newPhone !== currentPhone) {
        payload.phone_number = newPhone
    }
    
    if (newDate !== currentDate) {
        payload.birth_date = newDate
    }

    // 3. Если объект payload пустой — значит изменений нет
    if (Object.keys(payload).length === 0) {
        alert("Нет изменений для сохранения")
        return // Прерываем функцию, запрос не уйдет
    }

    // 4. Отправляем запрос только если есть реальные изменения
    try {
        const res = await api.put('/users/me', payload)
        
        // Обновляем локальные данные ответом от сервера
        if (res.data.username) currentUser.value.name = res.data.username
        if (res.data.phone_number !== undefined) currentUser.value.phone = res.data.phone_number
        if (res.data.birth_date !== undefined) currentUser.value.birthDate = res.data.birth_date
        
        alert("Профиль успешно обновлен!")
        isSettingsOpen.value = false
    } catch (e) {
        alert("Ошибка: " + (e.response?.data?.detail || e.message))
    }
}



const toggleSettings = () => {
    if (!isSettingsOpen.value) {
        // При открытии: копируем текущие данные во временную форму
        editingProfile.value = {
            name: currentUser.value.name,
            phone: currentUser.value.phone,
            birthDate: currentUser.value.birthDate
        }
    }
    isSettingsOpen.value = !isSettingsOpen.value
}

onMounted(async () => {
  const token = localStorage.getItem('access_token')
  if (!token) {
    router.push('/')
    return
  }

  try {
    const meRes = await api.get('/users/me')
    currentUser.value = {
      id: meRes.data.id,
      name: meRes.data.username,
      avatar: meRes.data.avatar_url ? (BASE_URL + meRes.data.avatar_url) : `https://ui-avatars.com/api/?name=${meRes.data.username}&background=0D8ABC&color=fff&bold=true`,
      phone: meRes.data.phone_number || '',
      birthDate: meRes.data.birth_date || ''
    }

    const usersRes = await api.get('/users')
    contacts.value = usersRes.data.map(u => ({
      id: u.id,
      name: u.username,
      status: u.is_online ? 'online' : 'offline', 
      avatar: u.avatar_url ? (BASE_URL + u.avatar_url) : `https://ui-avatars.com/api/?name=${u.username}&background=random`,
      lastMessage: u.last_message || 'Начните общение',
      time: u.last_message_time ? new Date(u.last_message_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''
    }))

    connectWebSocket()
  } catch (e) {
    console.error("Auth Failed", e)
    if (e.response && e.response.status === 401) logout()
  }
})

const selectChat = async (id) => {
  activeChatId.value = id
  if (!messages.value[id]) {
    try {
      const res = await api.get(`/messages/${id}`)
      messages.value[id] = res.data.map(m => ({
        id: m.id,
        senderId: m.sender_id,
        text: m.content,
        time: new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isRead: m.is_read
      }))
    } catch (e) {
      console.error("History Error", e)
    }
  }
  markAsRead(id)
  await nextTick()
  scrollToBottom()
}

const sendMessage = () => {
  if (!newMessage.value.trim() || !activeChatId.value) return
  const payload = { recipient_id: activeChatId.value, content: newMessage.value }

  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload))
    newMessage.value = ''
  } else {
    alert("Нет соединения")
  }
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const logout = () => {
  localStorage.removeItem('access_token')
  if (socket) socket.close()
  router.push('/')
}

onUnmounted(() => {
  if (socket) socket.close()
})
</script>

<template>
  <div class="messenger-layout">
    
    <!-- САЙДБАР -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="user-info">
          <img :src="currentUser.avatar" class="avatar-img-small" alt="me" />
          <span>{{ currentUser.name }}</span>
        </div>
        
        <div class="sidebar-actions">
            <!-- Кнопка настроек -->
            <button @click="toggleSettings" class="icon-btn" title="Настройки">
                <i class="fas fa-cog"></i> 
            </button>
            <!-- Кнопка выхода -->
            <button @click="logout" class="icon-btn" title="Выйти">
                <i class="fas fa-sign-out-alt"></i>
            </button>
        </div>
      </div>

      <div class="search-bar">
        <input type="text" placeholder="Поиск..." />
        <i class="fas fa-search"></i>
      </div>

      <div class="chat-list">
        <div 
          v-for="contact in contacts" 
          :key="contact.id"
          class="chat-item"
          :class="{ active: activeChatId === contact.id }"
          @click="selectChat(contact.id)"
        >
          <div class="avatar-wrapper">
            <img :src="contact.avatar" alt="Avatar" class="avatar-img" />
            <span class="status-dot" :class="contact.status"></span>
          </div>
          <div class="chat-info">
            <div class="chat-top">
              <span class="chat-name">{{ contact.name }}</span>
              <span class="chat-time">{{ contact.time }}</span>
            </div>
            <p class="chat-last-msg">{{ contact.lastMessage }}</p>
          </div>
        </div>
      </div>
    </aside>

    <!-- ОКНО ЧАТА -->
    <main class="chat-window" v-if="activeContact">
      <header class="chat-header">
        <div class="contact-profile">
          <img :src="activeContact.avatar" class="avatar-small" />
          <div class="contact-details">
            <h3>{{ activeContact.name }}</h3>
            <span class="status-text">{{ activeContact.status }}</span>
          </div>
        </div>
        <div class="header-actions">
           <button class="icon-btn"><i class="fas fa-ellipsis-v"></i></button>
        </div>
      </header>

      <div class="messages-area" ref="messagesContainer">
        <div 
          v-for="msg in currentMessages" 
          :key="msg.id" 
          class="message-row"
          :class="{ 'my-message': msg.senderId === currentUser.id }"
        >
          <div class="message-bubble">
            <p>{{ msg.text }}</p>
            <div class="msg-footer">
                <span class="message-time">{{ msg.time }}</span>
                <span v-if="msg.senderId === currentUser.id" class="checks" :class="msg.isRead ? 'read' : 'unread'">
                    {{ msg.isRead ? '✓✓' : '✓' }} 
                </span>
            </div>
          </div>
        </div>
        <div v-if="currentMessages.length === 0" class="empty-state">Напишите первое сообщение...</div>
      </div>

      <div class="input-area">
        <input 
          v-model="newMessage" 
          @keyup.enter="sendMessage"
          type="text" 
          placeholder="Напишите сообщение..." 
          autofocus 
        />
        <button @click="sendMessage" class="send-btn">
             <i class="fas fa-paper-plane"></i>
        </button>
      </div>
    </main>

    <main class="chat-window empty-chat" v-else>
        <p>Выберите чат, чтобы начать общение</p>
    </main>

    <!-- МОДАЛЬНОЕ ОКНО НАСТРОЕК -->
    <div v-if="isSettingsOpen" class="modal-overlay" @click.self="toggleSettings">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Настройки</h2>
          <button @click="toggleSettings" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <div class="settings-avatar">
             <img :src="currentUser.avatar" class="avatar-large" />
             <!-- Кнопка загрузки пока не активна -->
             <button class="upload-btn">Изменить фото</button> 
          </div>
          <div class="settings-form">
              <label>Имя пользователя</label>
              <!-- Привязываем к editingProfile, а не к currentUser -->
              <input type="text" v-model="editingProfile.name" /> 
              
              <label>Номер телефона</label>
              <input type="tel" v-model="editingProfile.phone" placeholder="+7 (999) 000-00-00" />
              
              <label>Дата рождения</label>
              <input type="date" v-model="editingProfile.birthDate" />
              
              <button @click="saveProfile" class="save-btn">Сохранить</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
:root {
  --color-bg: #0f172a;           
  --color-primary: #06b6d4;      
  --color-primary-dark: #0891b2; 
  --color-text-main: #f1f5f9;    
  --color-text-muted: #94a3b8;   
}

.messenger-layout { display: flex; height: 100vh; width: 100vw; background-color: var(--color-bg, #0f172a); color: var(--color-text-main, #f1f5f9); overflow: hidden; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
.sidebar { width: 300px; background: rgba(30, 41, 59, 0.5); border-right: 1px solid rgba(148, 163, 184, 0.1); display: flex; flex-direction: column; }
.sidebar-header { padding: 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
.user-info { display: flex; align-items: center; gap: 10px; font-weight: bold; }
.sidebar-actions { display: flex; gap: 10px; }
.avatar-img-small { width: 30px; height: 30px; border-radius: 50%; object-fit: cover; }
.search-bar { padding: 15px; position: relative; }
.search-bar input { width: 100%; padding: 10px 35px 10px 15px; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.1); background: rgba(0, 0, 0, 0.2); color: white; outline: none; }
.search-bar i { position: absolute; right: 25px; top: 50%; transform: translateY(-50%); color: #94a3b8; }
.chat-list { flex: 1; overflow-y: auto; }
.chat-item { display: flex; padding: 15px; cursor: pointer; transition: background 0.2s; border-left: 3px solid transparent; }
.chat-item:hover { background: rgba(255, 255, 255, 0.05); }
.chat-item.active { background: rgba(6, 182, 212, 0.1); border-left-color: #06b6d4; }
.avatar-wrapper { position: relative; margin-right: 15px; }
.avatar-img { width: 45px; height: 45px; border-radius: 50%; object-fit: cover; }
.status-dot { position: absolute; bottom: 2px; right: 2px; width: 10px; height: 10px; border-radius: 50%; border: 2px solid #1e293b; }
.status-dot.online { background: #10b981; }
.status-dot.offline { background: #64748b; }
.chat-info { flex: 1; overflow: hidden; }
.chat-top { display: flex; justify-content: space-between; margin-bottom: 5px; }
.chat-name { font-weight: 600; font-size: 15px; }
.chat-time { font-size: 12px; color: #94a3b8; }
.chat-last-msg { font-size: 13px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chat-window { flex: 1; display: flex; flex-direction: column; background: #0f172a; position: relative; }
.chat-window.empty-chat { display: flex; align-items: center; justify-content: center; color: #64748b; }
.chat-header { padding: 15px 25px; border-bottom: 1px solid rgba(148, 163, 184, 0.1); display: flex; justify-content: space-between; align-items: center; background: rgba(30, 41, 59, 0.3); }
.contact-profile { display: flex; align-items: center; gap: 15px; }
.avatar-small { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
.status-text { font-size: 12px; color: #06b6d4; }
.messages-area { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
.empty-state { text-align: center; margin-top: 50px; color: #475569; font-size: 0.9rem; }
.message-row { display: flex; margin-bottom: 5px; }
.message-row.my-message { justify-content: flex-end; }
.message-bubble { max-width: 60%; padding: 10px 15px; border-radius: 12px; background: #1e293b; position: relative; }
.my-message .message-bubble { background: linear-gradient(135deg, #0891b2, #2563eb); color: white; border-bottom-right-radius: 2px; }
.message-row:not(.my-message) .message-bubble { border-bottom-left-radius: 2px; }
.msg-footer { display: flex; justify-content: flex-end; align-items: center; margin-top: 5px; }
.message-time { font-size: 10px; color: rgba(255, 255, 255, 0.5); }
.checks { font-size: 0.9em; margin-left: 5px; font-weight: bold; }
.checks.read { color: #4ade80; }
.checks.unread { color: #94a3b8; }
.input-area { padding: 20px; background: rgba(30, 41, 59, 0.3); display: flex; gap: 10px; align-items: center; }
.input-area input { flex: 1; padding: 12px 20px; border-radius: 25px; border: 1px solid rgba(148, 163, 184, 0.2); background: rgba(15, 23, 42, 0.5); color: white; outline: none; }
.input-area input:focus { border-color: #06b6d4; }
.icon-btn, .send-btn, .close-btn { color: #94a3b8; font-size: 18px; padding: 10px; transition: color 0.2s; background: none; border: none; cursor: pointer; }
.icon-btn:hover, .close-btn:hover { color: white; }
.send-btn { color: #06b6d4; }
.send-btn:hover { transform: scale(1.1); }
.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.7); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal-content { background: #1e293b; width: 400px; border-radius: 12px; padding: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1); }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; }
.settings-avatar { display: flex; flex-direction: column; align-items: center; gap: 10px; margin-bottom: 20px; }
.avatar-large { width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid #06b6d4; }
.upload-btn { background: #0f172a; border: 1px solid #06b6d4; color: #06b6d4; padding: 5px 15px; border-radius: 20px; cursor: pointer; font-size: 0.9em; }
.settings-form label { display: block; margin-bottom: 5px; color: #94a3b8; font-size: 0.9em; }
.settings-form input { width: 100%; padding: 10px; margin-bottom: 15px; background: #0f172a; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: white; }
.save-btn { width: 100%; padding: 10px; background: #06b6d4; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; margin-top: 10px; }
.save-btn:hover { background: #0891b2; }
.disabled-input { opacity: 0.6; cursor: not-allowed; }
</style>
