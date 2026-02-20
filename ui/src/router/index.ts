import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 路由配置
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guest: true },
    },
    {
      path: '/',
      component: () => import('@/components/layout/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'apikeys',
          name: 'apikeys',
          component: () => import('@/views/apikey/ApiKeyList.vue'),
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('@/views/user/UserList.vue'),
          meta: { requiresSuperuser: true },
        },
      ],
    },
    // 404 页面
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 初始化认证状态
  if (!authStore.isLoggedIn && localStorage.getItem('token')) {
    await authStore.init()
  }

  // 需要登录的页面
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next('/login')
    return
  }

  // 需要超级用户权限的页面
  if (to.meta.requiresSuperuser && !authStore.isSuperuser) {
    next('/')
    return
  }

  // 游客页面（如登录页），已登录用户跳转到首页
  if (to.meta.guest && authStore.isLoggedIn) {
    next('/')
    return
  }

  next()
})

export default router
