import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import MainLayout from '@/views/MainLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/admin/sources',
    children: [
      {
        path: 'admin/sources',
        name: 'SourceList',
        component: () => import('@/views/SourceListPage.vue'),
        meta: { title: '源列表' },
      },
      {
        path: 'admin/sources/:id',
        name: 'SourceDetail',
        component: () => import('@/views/SourceDetailPage.vue'),
        meta: { title: '源详情' },
      },
      {
        path: 'admin/collections',
        name: 'Collections',
        component: () => import('@/views/CollectionPage.vue'),
        meta: { title: '合集管理' },
      },
      {
        path: 'admin/import',
        name: 'Import',
        component: () => import('@/views/ImportPage.vue'),
        meta: { title: '源导入' },
      },
      {
        path: 'admin/debug',
        name: 'Debug',
        component: () => import('@/views/DebugPage.vue'),
        meta: { title: '测试面板' },
      },
      {
        path: 'admin/batch-validate',
        name: 'BatchValidate',
        component: () => import('@/views/BatchValidatePage.vue'),
        meta: { title: '批量校验' },
      },
      {
        path: 'admin/devices',
        name: 'Devices',
        component: () => import('@/views/DevicePage.vue'),
        meta: { title: '真机管理' },
      },
      {
        path: 'admin/stats',
        name: 'Stats',
        component: () => import('@/views/StatsPage.vue'),
        meta: { title: '统计面板' },
      },
    ],
  },
  {
    path: '/legado/:pathMatch(.*)*',
    name: 'LegadoNative',
    component: () => import('@/views/LegadoNativePage.vue'),
    meta: { title: 'Legado 原生前端' },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
