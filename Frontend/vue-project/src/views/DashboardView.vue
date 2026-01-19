<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// --- МОКОВЫЕ ДАННЫЕ (Имитация базы данных) ---
const currentUser = ref({
  id: 1,
  name: 'Вы',
  avatar: 'https://i.pravatar.cc/150?u=me'
})

const contacts = ref([
  { id: 2, name: 'Alice Cyber', status: 'online', avatar: 'https://i.pravatar.cc/150?u=2', lastMessage: 'Ты видел новый протокол?', time: '10:42' },
  { id: 3, name: 'Bob Nexus', status: 'offline', avatar: 'https://i.pravatar.cc/150?u=3', lastMessage: 'Код ревью готов.', time: 'Вчера' },
  { id: 4, name: 'Sarah Tech', status: 'online', avatar: 'https://i.pravatar.cc/150?u=4', lastMessage: 'Отлично, запускаем!', time: 'Пн' },
])

// История сообщений (ключ = ID контакта)
const messages = ref({
  2: [
    { id: 1, senderId: 2, text: 'Привет! Как продвигается разработка?', time: '10:30' },
    { id: 2, senderId: 1, text: 'Привет, Алиса. Почти закончил авторизацию.', time: '10:32' },
    { id: 3, senderId: 2, text: 'Ты видел новый протокол?', time: '10:42' },
  ],
  3: [
    { id: 1, senderId: 3, text: 'Я запушил изменения в ветку dev.', time: '18:00' },
    { id: 2, senderId: 3, text: 'Код ревью готов.', time: '18:05' },
  ],
  4: []
})

// --- СОСТОЯНИЕ ИНТЕРФЕЙСА ---
const activeChatId = ref(2) // По умолчанию открыт чат с Alice
const newMessage = ref('')
const messagesContainer = ref(null) // Ссылка на блок с сообщениями для скролла

// Вычисляем активного собеседника
const activeContact = computed(() => {
  return contacts.value.find(c => c.id === activeChatId.value)
})

// Вычисляем сообщения текущего чата
const currentMessages = computed(() => {
  return messages.value[activeChatId.value] || []
})

// --- ЛОГИКА ---

// Скролл вниз при новом сообщении
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// Выбор чата
const selectChat = (id) => {
  activeChatId.value = id
  scrollToBottom()
  // На мобильных здесь можно закрывать меню
}

// Отправка сообщения
const sendMessage = () => {
  if (!newMessage.value.trim()) return

  // Добавляем сообщение в массив
  if (!messages.value[activeChatId.value]) {
    messages.value[activeChatId.value] = []
  }

  messages.value[activeChatId.value].push({
    id: Date.now(),
    senderId: currentUser.value.id,
    text: newMessage.value,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  })

  // Обновляем "последнее сообщение" в сайдбаре
  const contact = contacts.value.find(c => c.id === activeChatId.value)
  if (contact) {
    contact.lastMessage = newMessage.value
    contact.time = 'Сейчас'
  }

  newMessage.value = ''
  scrollToBottom()
}

const logout = () => {
  router.push('/')
}

onMounted(() => {
  scrollToBottom()
})
</script>

<template>
  <div class="messenger-layout">
    
    <!-- САЙДБАР (СПИСОК ЧАТОВ) -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="user-info">
          <div class="avatar me"><i class="fas fa-user-astronaut"></i></div>
          <span>{{ currentUser.name }}</span>
        </div>
        <button @click="logout" class="icon-btn" title="Выйти"><i class="fas fa-sign-out-alt"></i></button>
      </div>

      <div class="search-bar">
        <input type="text" placeholder="Поиск контактов...">
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
            <img :src="contact.avatar" alt="Avatar" class="avatar-img">
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

    <!-- ОСНОВНОЕ ОКНО ЧАТА -->
    <main class="chat-window">
      
      <!-- ШАПКА ЧАТА -->
      <header class="chat-header">
        <div class="contact-profile">
          <img :src="activeContact.avatar" class="avatar-small">
          <div class="contact-details">
            <h3>{{ activeContact.name }}</h3>
            <span class="status-text">{{ activeContact.status }}</span>
          </div>
        </div>
        <div class="header-actions">
          <button class="icon-btn"><i class="fas fa-phone"></i></button>
          <button class="icon-btn"><i class="fas fa-video"></i></button>
          <button class="icon-btn"><i class="fas fa-ellipsis-v"></i></button>
        </div>
      </header>

      <!-- ОБЛАСТЬ СООБЩЕНИЙ -->
      <div class="messages-area" ref="messagesContainer">
        <div 
          v-for="msg in currentMessages" 
          :key="msg.id" 
          class="message-row"
          :class="{ 'my-message': msg.senderId === currentUser.id }"
        >
          <div class="message-bubble">
            <p>{{ msg.text }}</p>
            <span class="message-time">{{ msg.time }}</span>
          </div>
        </div>
      </div>

      <!-- ВВОД СООБЩЕНИЯ -->
      <div class="input-area">
        <button class="attach-btn"><i class="fas fa-paperclip"></i></button>
        <input 
          v-model="newMessage" 
          @keyup.enter="sendMessage"
          type="text" 
          placeholder="Напишите сообщение..."
        >
        <button @click="sendMessage" class="send-btn">
          <i class="fas fa-paper-plane"></i>
        </button>
      </div>

    </main>
  </div>
</template>

<style scoped>
/* --- ЛЕЙАУТ --- */
.messenger-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  background-color: var(--color-bg); /* Берем из main.css */
  color: var(--color-text-main);
  overflow: hidden;
}

/* --- САЙДБАР --- */
.sidebar {
  width: 300px;
  background: rgba(20, 25, 40, 0.5); /* Полупрозрачный */
  border-right: 1px solid rgba(80, 120, 255, 0.1);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: bold;
}

.avatar.me {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #000;
}

.search-bar {
  padding: 15px;
  position: relative;
}

.search-bar input {
  width: 100%;
  padding: 10px 35px 10px 15px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
  color: white;
}

.search-bar i {
  position: absolute;
  right: 25px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-muted);
}

.chat-list {
  flex: 1;
  overflow-y: auto;
}

.chat-item {
  display: flex;
  padding: 15px;
  cursor: pointer;
  transition: background 0.2s;
  border-left: 3px solid transparent;
}

.chat-item:hover {
  background: rgba(255, 255, 255, 0.03);
}

.chat-item.active {
  background: rgba(0, 217, 255, 0.05);
  border-left-color: var(--color-primary);
}

.avatar-wrapper {
  position: relative;
  margin-right: 15px;
}

.avatar-img {
  width: 45px;
  height: 45px;
  border-radius: 50%;
  object-fit: cover;
}

.status-dot {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #1a1a1a;
}
.status-dot.online { background: #00ff88; }
.status-dot.offline { background: #555; }

.chat-info {
  flex: 1;
  overflow: hidden;
}

.chat-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.chat-name { font-weight: 600; font-size: 15px; }
.chat-time { font-size: 12px; color: var(--color-text-muted); }

.chat-last-msg {
  font-size: 13px;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* --- ОКНО ЧАТА --- */
.chat-window {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(10, 14, 23, 0.8);
  position: relative;
}

.chat-header {
  padding: 15px 25px;
  border-bottom: 1px solid rgba(80, 120, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(20, 25, 40, 0.3);
}

.contact-profile {
  display: flex;
  align-items: center;
  gap: 15px;
}

.avatar-small {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.status-text {
  font-size: 12px;
  color: var(--color-primary);
}

.messages-area {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.message-row {
  display: flex;
  margin-bottom: 5px;
}

.message-row.my-message {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 60%;
  padding: 10px 15px;
  border-radius: 12px;
  background: rgba(40, 45, 60, 0.6);
  position: relative;
}

.my-message .message-bubble {
  background: linear-gradient(135deg, var(--color-primary-dark), #005cbf);
  color: white;
  border-bottom-right-radius: 2px;
}

.message-row:not(.my-message) .message-bubble {
  border-bottom-left-radius: 2px;
}

.message-time {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  display: block;
  text-align: right;
  margin-top: 5px;
}

/* --- ВВОД --- */
.input-area {
  padding: 20px;
  background: rgba(20, 25, 40, 0.3);
  display: flex;
  gap: 10px;
  align-items: center;
}

.input-area input {
  flex: 1;
  padding: 12px 20px;
  border-radius: 25px;
  border: 1px solid rgba(80, 120, 255, 0.2);
  background: rgba(0, 0, 0, 0.3);
  color: white;
  outline: none;
}

.input-area input:focus {
  border-color: var(--color-primary);
}

.icon-btn, .attach-btn, .send-btn {
  color: var(--color-text-muted);
  font-size: 18px;
  padding: 10px;
  transition: color 0.2s;
}

.icon-btn:hover { color: white; }

.send-btn {
  color: var(--color-primary);
  transform: rotate(0deg); /* Для эффекта */
}
.send-btn:hover {
  transform: scale(1.1);
}
</style>
