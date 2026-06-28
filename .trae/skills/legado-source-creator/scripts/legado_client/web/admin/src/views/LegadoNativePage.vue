<template>
  <div class="legado-native-page">
    <iframe
      :src="legadoUrl"
      class="legado-iframe"
      frameborder="0"
      @load="onLoad"
    />
    <div v-if="loading" class="loading-mask">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p>连接 Legado 原生前端...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Loading } from '@element-plus/icons-vue'

const legadoUrl = '/legado/'
const loading = ref(true)

function onLoad() {
  loading.value = false
}
</script>

<style scoped>
.legado-native-page {
  position: relative;
  width: 100%;
  height: calc(100vh - 130px);
}

.legado-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.loading-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--el-bg-color);
  color: var(--el-text-color-secondary);
}
</style>
