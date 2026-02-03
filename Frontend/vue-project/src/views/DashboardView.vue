<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

// Импортируем компоненты
import ChatSidebar from '../components/ChatSidebar.vue'
import ChatWindow from '../components/ChatWindow.vue'
import UserProfileModal from '../components/UserProfileModal.vue'
import ContactInfoModal from '../components/ContactInfoModal.vue'

const router = useRouter()
const BASE_URL = 'http://localhost:8000' 
const api = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// --- ЗВУКОВОЕ УВЕДОМЛЕНИЕ ---
const notificationSound = new Audio('/notification.mp3')

// STATE
const isContactInfoOpen = ref(false)
const currentUser = ref({ id: null, name: 'Загрузка...', avatar: '', phone: '', birthDate: '' })
const contacts = ref([])
const messages = ref({}) 
const activeChatId = ref(null)
const isSettingsOpen = ref(false)
const isTyping = ref(false) 
let socket = null
let typingTimeout = null
let lastTypingSent = 0

// COMPUTED
const activeContact = computed(() => {
  if (!activeChatId.value) return null
  return contacts.value.find(c => c.id === activeChatId.value) || { name: 'Загрузка...', avatar: '', status: 'offline' }
})

const currentMessages = computed(() => {
  return activeChatId.value ? (messages.value[activeChatId.value] || []) : []
})

// HELPERS
const isImage = (text) => text && text.match(/\.(jpeg|jpg|gif|png|webp|bmp)$/i) != null
const isAudio = (text) => text && text.match(/\.(webm|mp3|wav|ogg)$/i) != null

const formatLastMessage = (content) => {
    if (!content) return 'Начните общение'
    if (isImage(content)) return '📷 Фото'
    if (isAudio(content)) return '🎤 Голосовое сообщение'
    if (content.startsWith('http')) return '📎 Файл'
    return content
}

// --- НОВОЕ: ПОИСК СООБЩЕНИЙ ---
const handleMessageSearch = async (query) => {
    if (!activeChatId.value) return

    // Если запрос пустой или null - загружаем обычную историю
    if (!query || query.trim() === '') {
        await selectChat(activeChatId.value) // Просто перезагружаем чат
        return
    }

    try {
        const res = await api.get(`/messages/${activeChatId.value}/search`, {
            params: { q: query }
        })
        
        // Мапим результат поиска в наш формат сообщений
        const foundMessages = res.data.map(m => ({
            id: m.id,
            senderId: m.sender_id,
            text: m.content,
            time: new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            isRead: m.is_read,
            rawDate: new Date(m.timestamp),
            replyTo: m.reply_to
        }))
        
        // ВАЖНО: Обновляем список сообщений для текущего чата
        messages.value[activeChatId.value] = foundMessages
        
    } catch (e) {
        console.error("Ошибка поиска:", e)
    }
}

// ACTIONS
const deleteMessage = (msgId) => {
    if (!confirm('Удалить сообщение?')) return
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'delete_message', message_id: msgId }))
    }
}
const editMessage = (msg) => {
    const newText = prompt('Редактировать сообщение:', msg.text)
    if (newText && newText !== msg.text && socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'edit_message', message_id: msg.id, new_content: newText }))
    }
}

const handleTypingInput = () => {
    const now = Date.now()
    if (now - lastTypingSent > 2000 && activeChatId.value && socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'typing', recipient_id: activeChatId.value }))
        lastTypingSent = now
    }
}

const handleSendMessage = (payload) => {
    // Если payload - это строка (для старых вызовов типа файлов), превращаем в объект
    const content = typeof payload === 'string' ? payload : payload.text
    const replyToId = typeof payload === 'object' ? payload.replyToId : null

    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ 
            type: 'message', 
            recipient_id: activeChatId.value, 
            content: content,
            reply_to_id: replyToId
        }))
    } else { alert("Нет соединения") }
}

const handleSendFile = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await api.post('/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
    handleSendMessage(res.data.url)
  } catch (e) { alert("Ошибка загрузки файла.") }
}

// ПРОФИЛЬ
const handleAvatarUpload = async (file, profileToUpdate) => {
    const formData = new FormData()
    formData.append('file', file)
    try {
        const res = await api.post('/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
        profileToUpdate.avatarUrl = res.data.url
    } catch (e) { alert("Ошибка загрузки фото: " + e) }
}

const saveProfile = async (updatedData) => {
    const payload = {}
    if (updatedData.name !== currentUser.value.name) payload.username = updatedData.name
    if (updatedData.phone !== currentUser.value.phone) payload.phone_number = updatedData.phone
    if (updatedData.birthDate !== currentUser.value.birthDate) payload.birth_date = updatedData.birthDate
    if (updatedData.avatarUrl !== currentUser.value.avatar) payload.avatar_url = updatedData.avatarUrl

    if (Object.keys(payload).length === 0) { alert("Нет изменений"); return }

    try {
        const res = await api.put('/users/me', payload)
        if (res.data.username) currentUser.value.name = res.data.username
        if (res.data.phone_number) currentUser.value.phone = res.data.phone_number
        if (res.data.birth_date) currentUser.value.birthDate = res.data.birth_date
        if (res.data.avatar_url) currentUser.value.avatar = res.data.avatar_url
        alert("Профиль обновлен!")
        isSettingsOpen.value = false
    } catch (e) {
        alert("Ошибка: " + (e.response?.data?.detail || e.message))
    }
}

// WEBSOCKET
const connectWebSocket = () => {
  const token = localStorage.getItem('access_token')
  if (!token) return
  const wsUrl = BASE_URL.replace('http', 'ws') + `/ws?token=${token}`
  socket = new WebSocket(wsUrl)
  
  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)

    if (data.type === 'status_update') {
        const contact = contacts.value.find(c => c.id === data.user_id)
        if (contact) contact.status = data.status
        return
    }
    if (data.type === 'user_typing') {
        if (activeChatId.value === data.sender_id) {
            isTyping.value = true
            if (typingTimeout) clearTimeout(typingTimeout)
            typingTimeout = setTimeout(() => { isTyping.value = false }, 3000)
        }
        return
    }
    if (data.type === 'messages_read') {
        const partnerId = data.user_id
        if (messages.value[partnerId]) messages.value[partnerId].forEach(msg => { if (msg.senderId === currentUser.value.id) msg.isRead = true })
        return
    }
    if (data.type === 'message_deleted') {
        for (const chatId in messages.value) messages.value[chatId] = messages.value[chatId].filter(m => m.id !== data.id)
        return
    }
    if (data.type === 'message_edited') {
        for (const chatId in messages.value) {
            const msg = messages.value[chatId].find(m => m.id === data.id)
            if (msg) msg.text = data.content
        }
        return
    }
    if (data.type === 'new_message') {
        const partnerId = data.sender_id === currentUser.value.id ? data.recipient_id : data.sender_id
        if (!messages.value[partnerId]) messages.value[partnerId] = []
        
        const exists = messages.value[partnerId].find(m => m.id === data.id)
        if (!exists) {
            messages.value[partnerId].push({
                id: data.id,
                senderId: data.sender_id,
                text: data.content,
                time: new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                isRead: data.is_read || false,
                rawDate: new Date(data.timestamp),
                replyTo: data.reply_to
            })
        }
        
        const contact = contacts.value.find(c => c.id === partnerId)
        if (contact) {
            contact.lastMessage = formatLastMessage(data.content)
            contact.time = new Date(data.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
        
        // ЗВУК
        if (data.sender_id !== currentUser.value.id) {
            if (activeChatId.value !== partnerId || document.hidden) {
                notificationSound.play().catch(err => console.log("Sound blocked by browser policy:", err))
            }
        }
        
        if (activeChatId.value === partnerId) {
            if (data.sender_id !== currentUser.value.id) {
                isTyping.value = false
                markAsRead(partnerId)
            }
        }
    }
  }
  socket.onclose = () => setTimeout(() => { if (localStorage.getItem('access_token')) connectWebSocket() }, 3000)
}

const markAsRead = (senderId) => {
    if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "read_messages", sender_id: senderId }))
}

const selectChat = async (id) => {
  activeChatId.value = id
  isTyping.value = false 
  // Мы всегда загружаем свежие данные при клике на чат (чтобы сбросить поиск если был)
  try {
      const res = await api.get(`/messages/${id}`)
      messages.value[id] = res.data.map(m => ({
        id: m.id,
        senderId: m.sender_id,
        text: m.content,
        time: new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isRead: m.is_read,
        rawDate: new Date(m.timestamp),
        replyTo: m.reply_to
      }))
  } catch (e) { console.error(e) }
  
  markAsRead(id)
}

onMounted(async () => {
  const token = localStorage.getItem('access_token')
  if (!token) { router.push('/'); return }
  try {
    const meRes = await api.get('/users/me')
    currentUser.value = {
      id: meRes.data.id,
      name: meRes.data.username,
      avatar: meRes.data.avatar_url || `https://ui-avatars.com/api/?name=${meRes.data.username}&background=0D8ABC&color=fff&bold=true`,
      phone: meRes.data.phone_number || '',
      birthDate: meRes.data.birth_date || ''
    }
    const usersRes = await api.get('/users')
    contacts.value = usersRes.data.map(u => ({
      id: u.id,
      name: u.username,
      phone: u.phone_number,
      birthDate: u.birth_date, 
      status: u.is_online ? 'online' : 'offline', 
      avatar: u.avatar_url || `https://ui-avatars.com/api/?name=${u.username}&background=random`,
      lastMessage: formatLastMessage(u.last_message),
      time: u.last_message_time ? new Date(u.last_message_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''
    }))
    connectWebSocket()
  } catch (e) { if (e.response?.status === 401) logout() }
})

const logout = () => { localStorage.removeItem('access_token'); if (socket) socket.close(); router.push('/') }
onUnmounted(() => { if (socket) socket.close() })
</script>


<template>
  <div class="messenger-layout">
    <ChatSidebar 
        :currentUser="currentUser" 
        :contacts="contacts" 
        :activeChatId="activeChatId"
        @select-chat="selectChat"
        @logout="logout"
        @open-settings="isSettingsOpen = true"
    />

    <!-- ДОБАВЛЕНО СОБЫТИЕ @search-in-chat -->
    <ChatWindow 
        v-if="activeContact"
        :activeContact="activeContact"
        :messages="currentMessages"
        :currentUserId="currentUser.id"
        :isTyping="isTyping"
        @send-message="handleSendMessage"
        @send-file="handleSendFile"
        @edit-message="editMessage"
        @delete-message="deleteMessage"
        @typing="handleTypingInput"
        @open-contact-info="isContactInfoOpen = true"
        @search-in-chat="handleMessageSearch" 
    />

    <main class="chat-window empty-chat" v-else>
        <p>Выберите чат, чтобы начать общение</p>
    </main>

    <UserProfileModal 
        :isOpen="isSettingsOpen"
        :currentUser="currentUser"
        @close="isSettingsOpen = false"
        @save="saveProfile"
        @upload-avatar="handleAvatarUpload"
    />

    <ContactInfoModal 
        :isOpen="isContactInfoOpen"
        :contact="activeContact"
        @close="isContactInfoOpen = false"
    />
  </div>
</template>

<style scoped>
.messenger-layout { display: flex; height: 100vh; width: 100vw; background-color: #0f172a; color: #f1f5f9; overflow: hidden; font-family: 'Segoe UI', sans-serif; }
.chat-window.empty-chat { flex: 1; display: flex; align-items: center; justify-content: center; color: #64748b; background: #0f172a; }
</style>
