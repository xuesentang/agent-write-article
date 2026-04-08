import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/Home.vue'),
      meta: { title: '首页' },
    },
    {
      path: '/create',
      name: 'create',
      component: () => import('@/views/Create.vue'),
      meta: { title: '创作文章' },
    },
    {
      path: '/result/:id',
      name: 'result',
      component: () => import('@/views/Result.vue'),
      meta: { title: '文章详情' },
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('@/views/History.vue'),
      meta: { title: '历史记录' },
    },
    {
      path: '/about',
      name: 'about',
      component: () => import('@/views/About.vue'),
      meta: { title: '关于我们' },
    },
    {
      path: '/sse-test',
      name: 'sse-test',
      component: () => import('@/views/SSETest.vue'),
      meta: { title: 'SSE 测试' },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFound.vue'),
      meta: { title: '页面未找到' },
    },
  ],
})

// 路由守卫：更新页面标题
router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string
  if (title) {
    document.title = `${title} - 自媒体爆款文章生成器`
  }
  next()
})

export default router