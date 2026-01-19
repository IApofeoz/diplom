import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '../views/LoginPage.vue' // 1. Импорт

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',           // 2. Главный путь
      name: 'login',
      component: LoginPage // 3. Компонент входа
    },
        {
      path: '/register',
      name: 'register',
      // Ленивая загрузка (лучше для производительности)
      component: () => import('../views/RegistrationPage.vue')
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      // Ленивая загрузка для остальных страниц (хорошая практика)
      component: () => import('../views/DashboardView.vue') 
    }
  ]
})

export default router
