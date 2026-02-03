<script setup>
import { ref, nextTick, watch, computed } from 'vue'
import AudioPlayer from './AudioPlayer.vue' 
import EmojiPicker from 'vue3-emoji-picker'
import 'vue3-emoji-picker/css'

const props = defineProps({
    activeContact: Object,
    messages: Array,
    currentUserId: Number,
    isTyping: Boolean
})

const emit = defineEmits([
    'send-message', 
    'send-file', 
    'edit-message', 
    'delete-message', 
    'typing', 
    'open-contact-info',
    'search-in-chat' // <--- НОВОЕ СОБЫТИЕ
])

const newMessage = ref('')
const messagesContainer = ref(null)
const fileInput = ref(null)
const isRecording = ref(false)
const showEmojiPicker = ref(false)
const replyingTo = ref(null) 

// --- НОВЫЕ ПЕРЕМЕННЫЕ ДЛЯ ПОИСКА ---
const showMsgSearch = ref(false)
const msgSearchQuery = ref('')

let mediaRecorder = null
let audioChunks = []

// --- ЛОГИКА ДАТ ---
const isSameDay = (d1, d2) => {
    return d1.getFullYear() === d2.getFullYear() &&
           d1.getMonth() === d2.getMonth() &&
           d1.getDate() === d2.getDate()
}

const getDateLabel = (date) => {
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    if (isSameDay(date, today)) return 'Сегодня'
    if (isSameDay(date, yesterday)) return 'Вчера'
    return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

const messagesWithDividers = computed(() => {
    const res = []
    let lastDate = null
    
    props.messages.forEach(msg => {
        const msgDate = msg.rawDate || new Date() 
        
        if (!lastDate || !isSameDay(lastDate, msgDate)) {
            res.push({ type: 'divider', text: getDateLabel(msgDate), id: 'div_' + msg.id })
            lastDate = msgDate
        }
        res.push({ type: 'message', ...msg })
    })
    return res
})

// --- ХЕЛПЕРЫ ---
const isImage = (text) => text && text.match(/\.(jpeg|jpg|gif|png|webp|bmp)$/i) != null
const isAudio = (text) => text && text.match(/\.(webm|mp3|wav|ogg)$/i) != null
const getFileName = (url) => {
    try { return decodeURIComponent(url).split('/').pop() } catch (e) { return "Скачать файл" }
}
const openImage = (url) => window.open(url, '_blank')

const formatReplyContent = (text) => {
    if (!text) return ''
    if (isAudio(text)) return '🎤 Голосовое сообщение'
    if (isImage(text)) return '📷 Фотография'
    if (text.startsWith('http')) return '📎 ' + getFileName(text)
    return text
}

const scrollToBottom = () => {
    if (messagesContainer.value) messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
}

// При изменении сообщений скроллим вниз (если не идет поиск)
// Если идет поиск, пользователь может смотреть старые сообщения, поэтому автоскролл может мешать
watch(() => props.messages, async () => {
    await nextTick()
    if (!showMsgSearch.value) {
        scrollToBottom()
    }
}, { deep: true })

watch(() => props.activeContact, async () => {
    // Сбрасываем поиск при смене чата
    closeSearch()
    await nextTick()
    scrollToBottom()
})

// --- ПОИСК СООБЩЕНИЙ ---
const performSearch = () => {
    if (!msgSearchQuery.value.trim()) return
    emit('search-in-chat', msgSearchQuery.value)
}

const closeSearch = () => {
    showMsgSearch.value = false
    msgSearchQuery.value = ''
    emit('search-in-chat', '') // Пустая строка = сброс фильтра, вернуть все сообщения
}

// --- ОТВЕТЫ (REPLY) ---
const startReply = (msg) => {
    replyingTo.value = msg
    nextTick(() => document.querySelector('.chat-input')?.focus())
}

const cancelReply = () => {
    replyingTo.value = null
}

const onSend = () => {
    if(!newMessage.value.trim()) return
    
    emit('send-message', { 
        text: newMessage.value, 
        replyToId: replyingTo.value ? replyingTo.value.id : null 
    })
    
    newMessage.value = ''
    replyingTo.value = null
    showEmojiPicker.value = false 
}

const onTyping = () => { emit('typing') }

const triggerFileUpload = () => fileInput.value.click()
const handleFile = (e) => {
    const file = e.target.files[0]
    if(file) emit('send-file', file)
}

const onSelectEmoji = (emoji) => {
    newMessage.value += emoji.i 
    onTyping() 
}

const toggleEmojiPicker = () => { showEmojiPicker.value = !showEmojiPicker.value }

// --- ЗАПИСЬ ГОЛОСА ---
const startRecording = async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        mediaRecorder = new MediaRecorder(stream)
        audioChunks = []
        mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data)
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
            const audioFile = new File([audioBlob], "voice_message.webm", { type: "audio/webm" })
            emit('send-file', audioFile)
        }
        mediaRecorder.start()
        isRecording.value = true
        showEmojiPicker.value = false 
    } catch (err) { alert("Ошибка микрофона: " + err) }
}

const stopRecording = () => {
    if (mediaRecorder && isRecording.value) {
        mediaRecorder.stop()
        isRecording.value = false
        mediaRecorder.stream.getTracks().forEach(track => track.stop())
    }
}

const cancelRecording = () => {
    if (mediaRecorder && isRecording.value) {
        mediaRecorder.onstop = null
        mediaRecorder.stop()
        isRecording.value = false
        mediaRecorder.stream.getTracks().forEach(track => track.stop())
        audioChunks = []
    }
}
</script>

<template>
    <main class="chat-window" v-if="activeContact">
      <header class="chat-header">
        
        <!-- ОБЫЧНЫЙ РЕЖИМ: Аватар и Имя -->
        <div class="contact-profile" v-if="!showMsgSearch">
          <img :src="activeContact.avatar" class="avatar-small" />
          <div class="contact-details">
            <h3>{{ activeContact.name }}</h3>
            <span v-if="isTyping" class="typing-text">печатает...</span>
            <span v-else class="status-text">{{ activeContact.status }}</span>
          </div>
        </div>

        <!-- РЕЖИМ ПОИСКА: Поле ввода -->
        <div class="search-input-wrapper" v-else>
            <input 
                v-model="msgSearchQuery" 
                @keyup.enter="performSearch"
                type="text" 
                placeholder="Поиск по истории..." 
                class="header-search-input"
                autofocus
            />
            <span class="search-hint" v-if="messages.length > 0 && msgSearchQuery">Найдено: {{ messages.length }}</span>
        </div>

        <div class="header-actions">
            <!-- Кнопка Лупы -->
            <button v-if="!showMsgSearch" class="icon-btn" @click="showMsgSearch = true" title="Поиск сообщений">
                <i class="fas fa-search"></i>
            </button>
            
            <!-- Кнопка Закрыть поиск -->
            <button v-else class="icon-btn close-search" @click="closeSearch" title="Закрыть поиск">
                <i class="fas fa-times"></i>
            </button>

            <!-- Кнопка Опции -->
            <button class="icon-btn" @click="$emit('open-contact-info')">
                <i class="fas fa-ellipsis-v"></i>
            </button>
        </div>
      </header>

      <div class="messages-area" ref="messagesContainer">
        <!-- Если поиск ничего не дал -->
        <div v-if="showMsgSearch && messages.length === 0" class="empty-state">
            Ничего не найдено по запросу "{{ msgSearchQuery }}"
        </div>

        <div v-for="item in messagesWithDividers" :key="item.id">
            
            <div v-if="item.type === 'divider'" class="date-divider"><span>{{ item.text }}</span></div>

            <div v-else class="message-row" :class="{ 'my-message': item.senderId === currentUserId }">
                <div class="message-bubble group">
                    
                    <!-- БЛОК ЦИТАТЫ -->
                    <div v-if="item.replyTo" class="reply-quote">
                        <div class="reply-line"></div>
                        <div class="reply-content">
                            <span class="reply-sender">{{ item.replyTo.sender_username }}</span>
                            <p class="reply-text">{{ formatReplyContent(item.replyTo.content) }}</p>
                        </div>
                    </div>
                    
                    <img v-if="isImage(item.text)" :src="item.text" class="msg-image" @click="openImage(item.text)" />
                    <AudioPlayer v-else-if="isAudio(item.text)" :src="item.text" />
                    
                    <a v-else-if="item.text.startsWith('http')" :href="item.text" target="_blank" class="msg-file">
                        <div class="file-icon"><i class="fas fa-file-alt"></i></div>
                        <div class="file-info"><span class="file-name">{{ getFileName(item.text) }}</span><span class="file-type">Документ</span></div>
                    </a>

                    <p v-else>{{ item.text }}</p>

                    <div class="msg-actions">
                        <button @click.stop="startReply(item)" class="action-btn" title="Ответить"><i class="fas fa-reply"></i></button>
                        <template v-if="item.senderId === currentUserId">
                            <button v-if="!isAudio(item.text) && !isImage(item.text) && !item.text.startsWith('http')" @click.stop="$emit('edit-message', item)" class="action-btn">✎</button>
                            <button @click.stop="$emit('delete-message', item.id)" class="action-btn delete">×</button>
                        </template>
                    </div>

                    <div class="msg-footer">
                        <span class="message-time">{{ item.time }}</span>
                        <span v-if="item.senderId === currentUserId" class="checks" :class="item.isRead ? 'read' : 'unread'">{{ item.isRead ? '✓✓' : '✓' }}</span>
                    </div>
                </div>
            </div>
        </div>
        <div v-if="messages.length === 0 && !showMsgSearch" class="empty-state">Напишите первое сообщение...</div>
      </div>

      <div v-if="showEmojiPicker" class="emoji-popover">
          <EmojiPicker :native="true" @select="onSelectEmoji" theme="dark" />
      </div>

      <!-- ПАНЕЛЬ ОТВЕТА (ПРЕДПРОСМОТР) -->
      <div v-if="replyingTo" class="reply-preview-bar">
          <div class="reply-info">
              <span class="reply-label">Ответ для {{ replyingTo.senderId === currentUserId ? 'себя' : activeContact.name }}</span>
              <p class="reply-text-preview">{{ formatReplyContent(replyingTo.text) }}</p>
          </div>
          <button @click="cancelReply" class="close-reply-btn">×</button>
      </div>

      <div class="input-area">
        <input type="file" ref="fileInput" @change="handleFile" style="display: none" />
        <button @click="triggerFileUpload" class="attach-btn"><i class="fas fa-paperclip"></i></button>
        <button @click="toggleEmojiPicker" class="emoji-btn"><i class="far fa-smile"></i></button>

        <input 
            v-model="newMessage" 
            @keyup.enter="onSend" 
            @input="onTyping"
            type="text" 
            class="chat-input"
            :placeholder="isRecording ? 'Запись голоса...' : 'Напишите сообщение...'" 
            autofocus 
            :disabled="isRecording" 
        />
        
        <template v-if="isRecording">
            <button @click="cancelRecording" class="cancel-btn"><i class="fas fa-times"></i></button>
            <button @click="stopRecording" class="record-btn recording"><i class="fas fa-stop"></i></button>
        </template>
        <button v-else-if="!newMessage.trim()" @click="startRecording" class="record-btn"><i class="fas fa-microphone"></i></button>
        <button v-else @click="onSend" class="send-btn"><i class="fas fa-paper-plane"></i></button>
      </div>
    </main>

    <main class="chat-window empty-chat" v-else>
        <p>Выберите чат, чтобы начать общение</p>
    </main>
</template>

<style scoped>
/* ОСНОВНОЙ ЛЕЙАУТ */
.chat-window { flex: 1; display: flex; flex-direction: column; background: #0f172a; position: relative; }
.chat-window.empty-chat { display: flex; align-items: center; justify-content: center; color: #64748b; }
.chat-header { height: 70px; padding: 0 25px; border-bottom: 1px solid rgba(148, 163, 184, 0.1); display: flex; justify-content: space-between; align-items: center; background: rgba(30, 41, 59, 0.3); }

/* ПРОФИЛЬ */
.contact-profile { display: flex; align-items: center; gap: 15px; }
.avatar-small { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
.status-text { font-size: 12px; color: #06b6d4; }
.typing-text { font-size: 12px; color: #06b6d4; font-style: italic; animation: pulse 1.5s infinite; }

/* ПОИСК В ХЕДЕРЕ */
.search-input-wrapper { flex: 1; display: flex; align-items: center; margin-right: 15px; position: relative; }
.header-search-input { width: 100%; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.1); padding: 8px 15px; border-radius: 20px; color: white; outline: none; transition: border 0.2s; }
.header-search-input:focus { border-color: #06b6d4; }
.search-hint { font-size: 11px; color: #94a3b8; position: absolute; right: 15px; }
.header-actions { display: flex; gap: 5px; }
.close-search { color: #ef4444 !important; }

/* СООБЩЕНИЯ */
.messages-area { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
.empty-state { text-align: center; margin-top: 50px; color: #475569; font-size: 0.9rem; }
.message-row { display: flex; margin-bottom: 5px; }
.message-row.my-message { justify-content: flex-end; }
.message-bubble { max-width: 60%; padding: 10px 15px; border-radius: 12px; background: #1e293b; position: relative; min-width: 120px; }
.my-message .message-bubble { background: linear-gradient(135deg, #0891b2, #2563eb); color: white; border-bottom-right-radius: 2px; }
.message-row:not(.my-message) .message-bubble { border-bottom-left-radius: 2px; }
.msg-image { max-width: 100%; max-height: 300px; border-radius: 8px; cursor: pointer; border: 1px solid rgba(255,255,255,0.1); }

/* ФАЙЛЫ, ДАТЫ, ЦИТАТЫ (Без изменений стилей, только компактность) */
.msg-file { display: flex; align-items: center; gap: 12px; background: rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 8px; text-decoration: none; color: inherit; transition: background 0.2s; min-width: 200px; }
.msg-file:hover { background: rgba(255, 255, 255, 0.1); }
.file-icon { width: 40px; height: 40px; background: rgba(6, 182, 212, 0.2); color: #06b6d4; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; }
.file-info { display: flex; flex-direction: column; }
.file-name { font-weight: 500; font-size: 14px; word-break: break-all; }
.file-type { font-size: 11px; color: #94a3b8; margin-top: 2px; }
.date-divider { display: flex; justify-content: center; margin: 20px 0; position: relative; }
.date-divider span { background: rgba(255, 255, 255, 0.1); color: #94a3b8; font-size: 12px; padding: 4px 12px; border-radius: 12px; font-weight: 500; }
.reply-quote { display: flex; gap: 10px; margin-bottom: 8px; background: rgba(0,0,0,0.2); padding: 5px 10px; border-radius: 6px; cursor: pointer; border-left: 3px solid #06b6d4; }
.reply-content { display: flex; flex-direction: column; font-size: 12px; overflow: hidden; }
.reply-sender { color: #cbd5e1; font-weight: bold; margin-bottom: 2px; font-size: 11px; }
.reply-text { color: rgba(255,255,255,0.8); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; margin: 0; }
.my-message .reply-sender { color: rgba(255,255,255,0.9); }
.reply-preview-bar { background: #1e293b; padding: 10px 20px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; align-items: center; animation: slideUp 0.2s; }
.reply-info { border-left: 3px solid #06b6d4; padding-left: 10px; }
.reply-label { color: #06b6d4; font-size: 12px; font-weight: bold; display: block; }
.reply-text-preview { color: #94a3b8; font-size: 13px; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 300px; }
.close-reply-btn { background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer; }

/* ДЕЙСТВИЯ СООБЩЕНИЙ */
.message-bubble:hover .msg-actions { display: flex; }
.msg-actions { position: absolute; top: -35px; right: 0; background: #1e293b; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; display: none; padding: 3px; z-index: 10; gap: 5px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
.action-btn { background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 14px; padding: 6px 10px; border-radius: 4px; transition: 0.2s; }
.action-btn:hover { background: rgba(255,255,255,0.1); color: white; }
.action-btn.delete:hover { color: #ef4444; }
.msg-footer { display: flex; justify-content: flex-end; align-items: center; margin-top: 5px; }
.message-time { font-size: 10px; color: rgba(255, 255, 255, 0.5); }
.checks { font-size: 0.9em; margin-left: 5px; font-weight: bold; color: #4ade80; }
.checks.unread { color: #94a3b8; }

/* INPUT AREA */
.input-area { padding: 20px; background: rgba(30, 41, 59, 0.3); display: flex; gap: 10px; align-items: center; position: relative; } 
.input-area input { flex: 1; padding: 12px 20px; border-radius: 25px; border: 1px solid rgba(148, 163, 184, 0.2); background: rgba(15, 23, 42, 0.5); color: white; outline: none; }
.input-area input:focus { border-color: #06b6d4; }
.input-area input:disabled { opacity: 0.5; cursor: not-allowed; }
.icon-btn, .send-btn, .attach-btn, .record-btn, .cancel-btn, .emoji-btn { color: #94a3b8; font-size: 18px; padding: 10px; background: none; border: none; cursor: pointer; transition: 0.2s; }
.icon-btn:hover, .attach-btn:hover, .emoji-btn:hover { color: white; }
.send-btn { color: #06b6d4; } 
.send-btn:hover { transform: scale(1.1); }
.record-btn:hover { color: white; }
.record-btn.recording { color: #ef4444; animation: pulse-red 1s infinite; }
.cancel-btn:hover { color: #ef4444; transform: scale(1.1); }
.emoji-popover { position: absolute; bottom: 80px; left: 20px; z-index: 100; box-shadow: 0 5px 20px rgba(0,0,0,0.5); border-radius: 8px; overflow: hidden; }

@keyframes pulse { 0% { opacity: 0.5; } 50% { opacity: 1; } 100% { opacity: 0.5; } }
@keyframes pulse-red { 0% { transform: scale(1); } 50% { transform: scale(1.2); } 100% { transform: scale(1); } }
@keyframes slideUp { from { transform: translateY(10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
</style>
