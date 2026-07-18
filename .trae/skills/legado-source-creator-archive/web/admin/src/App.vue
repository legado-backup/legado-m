<template>
  <router-view />
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

// 初始化暗色模式
appStore.initDarkMode()
</script>
