<script setup>
import { ref, computed, watch } from 'vue'
import axios from 'axios'
import _ from 'lodash' // Если lodash не установлен: npm install lodash

const props = defineProps({
    currentUser: Object,
    contacts: Array,
    activeChatId: Number
})

const emit = defineEmits(['select-chat', 'logout', 'open-settings'])

const searchQuery = ref('')
const globalSearchResults = ref([])
const isSearchingGlobal = ref(false)

// 1. Локальная фильтрация (среди уже загруженных чатов)
const filteredLocalContacts = computed(() => {
    if (!searchQuery.value) return props.contacts
    return props.contacts.filter(c => 
        c.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
})

// 2. Функция глобального поиска (debounce чтобы не дудосить сервер)
const performGlobalSearch = _.debounce(async (query) => {
    if (!query || query.length < 1) {
        globalSearchResults.value = []
        isSearchingGlobal.value = false
        return
    }

    // Если локально уже нашли именно того, кого искали - глобальный поиск можно не делать (опционально)
    // Но часто бывает, что есть чат с "Alex", а мы ищем нового "Alexander"

    isSearchingGlobal.value = true
    try {
        const token = localStorage.getItem('token')
        const response = await axios.get(`http://localhost:8000/users/search?q=${query}`, {
             headers: { Authorization: `Bearer ${token}` }
        })
        
        // Мапим ответ сервера в формат контактов
        globalSearchResults.value = response.data.map(u => ({
            id: u.id,
            name: u.username,
            avatar: u.avatar_url ? `http://localhost:8000${u.avatar_url}` : 'https://api.dicebear.com/7.x/avataaars/svg?seed=' + u.username,
            status: 'offline', // Статус неизвестен при поиске
            lastMessage: 'Нажмите, чтобы начать чат',
            time: ''
        }))
    } catch (error) {
        console.error("Ошибка поиска:", error)
    } finally {
        isSearchingGlobal.value = false
    }
}, 400)

// Следим за вводом
watch(searchQuery, (newVal) => {
    performGlobalSearch(newVal)
})

// Объединенный список: Сначала локальные совпадения, потом глобальные (исключая дубликаты)
const displayContacts = computed(() => {
    if (!searchQuery.value) return props.contacts

    const localIds = new Set(filteredLocalContacts.value.map(c => c.id))
    
    // Берем глобальные результаты, которых нет в локальных
    const uniqueGlobal = globalSearchResults.value.filter(u => !localIds.has(u.id))
    
    return [...filteredLocalContacts.value, ...uniqueGlobal]
})

</script>

<template>
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="user-info">
          <img :src="currentUser.avatar" class="avatar-img-small" />
          <span>{{ currentUser.name }}</span>
        </div>
        <div class="sidebar-actions">
            <button @click="$emit('open-settings')" class="icon-btn"><i class="fas fa-cog"></i></button>
            <button @click="$emit('logout')" class="icon-btn"><i class="fas fa-sign-out-alt"></i></button>
        </div>
      </div>

      <div class="search-bar">
        <input type="text" v-model="searchQuery" placeholder="Поиск пользователей..." />
        <i v-if="!isSearchingGlobal" class="fas fa-search"></i>
        <i v-else class="fas fa-spinner fa-spin"></i> <!-- Индикатор загрузки -->
      </div>

      <div class="chat-list">
        <!-- Если список пуст при поиске -->
        <div v-if="searchQuery && displayContacts.length === 0 && !isSearchingGlobal" class="no-results">
            Пользователь не найден
        </div>

        <div v-for="contact in displayContacts" :key="contact.id" class="chat-item" :class="{ active: activeChatId === contact.id }" @click="$emit('select-chat', contact.id)">
          <div class="avatar-wrapper">
            <img :src="contact.avatar" class="avatar-img" />
            <!-- Показываем статус только для локальных контактов (или если сервер отдает статус в поиске) -->
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
</template>

<style scoped>
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
.icon-btn { color: #94a3b8; font-size: 18px; padding: 10px; background: none; border: none; cursor: pointer; transition: 0.2s; }
.icon-btn:hover { color: white; }
.no-results { padding: 20px; text-align: center; color: #94a3b8; font-size: 14px; }
</style>
