<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios' // 1. Не забудьте импортировать axios

const router = useRouter()

// --- ПЕРЕМЕННЫЕ ФОРМЫ ---
const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false) // Добавим индикатор загрузки для кнопки

// --- ЛОГИКА РЕГИСТРАЦИИ (FastAPI) ---
const handleRegister = async () => {
  // 1. Проверка паролей
  if (password.value !== confirmPassword.value) {
    alert('Пароли не совпадают!')
    return
  }
  
  // Включаем спиннер
  isLoading.value = true

  try {
    // 2. Реальный запрос к вашему Python серверу
    // (Убедитесь, что backend/main.py запущен на порту 8000)
    const response = await axios.post('http://127.0.0.1:8000/register', {
      email: email.value,
      username: username.value,
      password: password.value
    })

    console.log('Ответ сервера:', response.data)
    
    // 3. Успех
    alert(`Регистрация успешна! Добро пожаловать, ${response.data.email}`)
    router.push('/') // Переход на страницу входа
    
  } catch (error) {
    console.error('Ошибка:', error)
    // Показываем ошибку от сервера (например, "Такой email уже занят") или общую
    const errorMsg = error.response?.data?.detail || 'Ошибка соединения с сервером'
    alert(errorMsg)
  } finally {
    isLoading.value = false // Выключаем спиннер в любом случае
  }
}

// --- ЛОГИКА CANVAS АНИМАЦИИ ---
// (Код полностью идентичен LoginPage.vue)
const canvasRef = ref(null)
let ctx = null
let animationFrameId = null
let points = []
const pointsCount = 80
let mouseX = 0
let mouseY = 0

class Point {
  constructor(w, h) {
    this.x = Math.random() * w
    this.y = Math.random() * h
    this.size = Math.random() * 3 + 1
    this.speedX = Math.random() * 2 - 1
    this.speedY = Math.random() * 2 - 1
    this.originalSize = this.size
  }
  
  update(w, h) {
    this.x += this.speedX
    this.y += this.speedY
    if (this.x <= 0 || this.x >= w) this.speedX = -this.speedX
    if (this.y <= 0 || this.y >= h) this.speedY = -this.speedY
    
    const dx = mouseX - this.x
    const dy = mouseY - this.y
    const distance = Math.sqrt(dx * dx + dy * dy)
    
    if (distance < 150) {
      this.size = this.originalSize + (150 - distance) / 30
      const force = (150 - distance) / 150
      this.x -= dx * force * 0.05
      this.y -= dy * force * 0.05
    } else {
      this.size = this.originalSize
    }
  }
  
  draw() {
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(100, 150, 255, 0.8)`
    ctx.fill()
  }
}

const initCanvas = () => {
  const canvas = canvasRef.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
  points = []
  for (let i = 0; i < pointsCount; i++) {
    points.push(new Point(canvas.width, canvas.height))
  }
}

const animate = () => {
  const canvas = canvasRef.value
  if (!canvas) return
  ctx.fillStyle = 'rgba(10, 14, 23, 0.1)'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  points.forEach(point => {
    point.update(canvas.width, canvas.height)
    point.draw()
  })
  for (let i = 0; i < points.length; i++) {
    for (let j = i + 1; j < points.length; j++) {
      const dx = points[i].x - points[j].x
      const dy = points[i].y - points[j].y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 150) {
        ctx.beginPath()
        ctx.moveTo(points[i].x, points[i].y)
        ctx.lineTo(points[j].x, points[j].y)
        ctx.strokeStyle = `rgba(100, 150, 255, ${1 - dist/150})`
        ctx.lineWidth = 0.5
        ctx.stroke()
      }
    }
  }
  animationFrameId = requestAnimationFrame(animate)
}

const onMouseMove = (e) => {
  mouseX = e.clientX
  mouseY = e.clientY
}

const onWindowResize = () => {
  if (canvasRef.value) {
    canvasRef.value.width = window.innerWidth
    canvasRef.value.height = window.innerHeight
  }
}

onMounted(() => {
  initCanvas()
  animate()
  window.addEventListener('resize', onWindowResize)
  window.addEventListener('mousemove', onMouseMove)
})

onUnmounted(() => {
  cancelAnimationFrame(animationFrameId)
  window.removeEventListener('resize', onWindowResize)
  window.removeEventListener('mousemove', onMouseMove)
})
</script>

<template>
  <div class="page-container">
    <canvas ref="canvasRef" id="background-canvas"></canvas>
    
    <div class="container">
      <div class="auth-card">
        <div class="logo">
          <i class="fas fa-user-astronaut"></i>
          <h1>СОЗДАНИЕ АККАУНТА</h1>
          <p>Присоединяйтесь к будущему</p>
        </div>

        <form @submit.prevent="handleRegister">
          <!-- Поле Имя -->
          <div class="input-group">
            <label for="username"><i class="fas fa-user"></i> Имя пользователя</label>
            <input type="text" id="username" v-model="username" placeholder="Придумайте логин" required>
            <i class="fas fa-user-circle input-icon"></i>
          </div>
          
          <!-- Поле Email -->
          <div class="input-group">
            <label for="email"><i class="fas fa-envelope"></i> Email адрес</label>
            <input type="email" id="email" v-model="email" placeholder="example@mail.com" required>
            <i class="fas fa-at input-icon"></i>
          </div>

          <!-- Поле Пароль -->
          <div class="input-group">
            <label for="password"><i class="fas fa-lock"></i> Пароль</label>
            <input type="password" id="password" v-model="password" placeholder="Введите пароль" required>
            <i class="fas fa-key input-icon"></i>
          </div>

          <!-- Поле Повтор пароля -->
          <div class="input-group">
            <label for="confirm"><i class="fas fa-check-double"></i> Повтор пароля</label>
            <input type="password" id="confirm" v-model="confirmPassword" placeholder="Повторите пароль" required>
            <i class="fas fa-lock input-icon"></i>
          </div>

          <button type="submit" class="auth-button">
             Зарегистрироваться
          </button>

          <div class="signup-link">
            Уже есть аккаунт? 
            <RouterLink to="/">Войти</RouterLink>
          </div>
        </form>
      </div>
    </div>
    <div class="footer">
      &copy; 2026 Future Auth. Все права защищены.
    </div>
  </div>
</template>

<style scoped>
/* СТИЛИ */
.page-container {
  width: 100vw;
  min-height: 100vh;
  position: relative;
}

#background-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
  position: relative;
  z-index: 1;
}

.auth-card {
  background: var(--color-bg-card);
  backdrop-filter: blur(10px);
  border-radius: var(--border-radius);
  padding: 40px 35px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(80, 120, 255, 0.2);
  position: relative;
  overflow: hidden;
}

.auth-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-dark), var(--color-primary));
  background-size: 200% 100%;
  animation: shimmer 3s infinite linear;
  z-index: 2;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.logo {
  text-align: center;
  margin-bottom: 30px;
}

.logo i {
  font-size: 42px;
  color: var(--color-primary);
  margin-bottom: 10px;
  text-shadow: var(--shadow-glow);
}

.logo h1 {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(to right, var(--color-primary), var(--color-primary-dark));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  letter-spacing: 1px;
}

.logo p {
  font-size: 14px;
  color: var(--color-text-muted);
  margin-top: 5px;
}

.input-group {
  margin-bottom: 25px;
  position: relative;
}

.input-group label {
  display: block;
  margin-bottom: 8px;
  color: #b0b0d0;
  font-size: 14px;
  font-weight: 500;
}

.input-group input {
  width: 100%;
  padding: 14px 16px;
  background: rgba(10, 15, 30, 0.7);
  border: 1px solid rgba(80, 120, 255, 0.3);
  border-radius: 8px;
  color: #fff;
  font-size: 16px;
  transition: all 0.3s ease;
}

.input-group input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 15px rgba(0, 217, 255, 0.3);
}

.input-icon {
  position: absolute;
  right: 16px;
  top: 40px;
  color: var(--color-primary);
  font-size: 18px;
}

.auth-button {
  width: 100%;
  padding: 16px;
  background: linear-gradient(90deg, #00a8ff, var(--color-primary-dark));
  border-radius: 8px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  letter-spacing: 1px;
  text-transform: uppercase;
  border: none;
}

.auth-button:hover {
  background: linear-gradient(90deg, var(--color-primary-dark), #00a8ff);
  box-shadow: 0 5px 20px rgba(0, 128, 255, 0.4);
  transform: translateY(-2px);
}

.auth-button:active {
  transform: translateY(0);
}

.signup-link {
  text-align: center;
  margin-top: 30px;
  font-size: 15px;
  color: var(--color-text-muted);
}

.signup-link a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
  margin-left: 5px;
}

.signup-link a:hover {
  text-decoration: underline;
}

.footer { position: absolute; bottom: 20px; width: 100%; text-align: center; color: #707090; font-size: 13px; z-index: 1; }

</style>
