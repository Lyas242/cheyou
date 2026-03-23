import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/BasicLayout.vue'),
    redirect: '/chat',
    children: [
      {
        path: 'chat',
        name: 'ChatConsole',
        component: () => import('@/views/ChatConsole.vue'),
        meta: {
          title: '智能选车'
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 车策` : '车策'
  next()
})

export default router
