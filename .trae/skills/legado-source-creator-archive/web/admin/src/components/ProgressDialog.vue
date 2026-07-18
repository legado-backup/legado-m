<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="500px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="closable"
  >
    <div class="progress-content">
      <el-progress
        :percentage="percentage"
        :status="status"
        :stroke-width="20"
        :text-inside="true"
      />
      <p v-if="message" class="progress-message">{{ message }}</p>
      <div v-if="details.length > 0" class="progress-details">
        <p v-for="(d, i) in details" :key="i">{{ d }}</p>
      </div>
    </div>
    <template #footer>
      <el-button v-if="closable" @click="visible = false">关闭</el-button>
      <el-button v-if="cancellable && !closable" type="danger" @click="handleCancel">取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: boolean
  title?: string
  percentage?: number
  message?: string
  details?: string[]
  cancellable?: boolean
  closable?: boolean
}>(), {
  title: '处理中...',
  percentage: 0,
  message: '',
  details: () => [],
  cancellable: false,
  closable: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'cancel': []
}>()

const visible = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  visible.value = val
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

// 进度状态
const status = ref<'' | 'success' | 'warning' | 'exception'>(() => {
  if (props.percentage >= 100) return 'success'
  return ''
})

watch(() => props.percentage, (val) => {
  status.value = val >= 100 ? 'success' : ''
})

function handleCancel() {
  emit('cancel')
}
</script>

<style scoped>
.progress-content {
  padding: 8px 0;
}

.progress-message {
  margin-top: 12px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.progress-details {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
