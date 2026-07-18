<template>
  <el-select
    v-model="selectedId"
    :placeholder="placeholder"
    clearable
    @change="handleChange"
  >
    <el-option
      v-for="device in devices"
      :key="device.id"
      :label="`${device.name} (${device.address})`"
      :value="device.id"
    >
      <span>{{ device.name }}</span>
      <el-tag
        :type="device.online ? 'success' : 'info'"
        size="small"
        style="margin-left: 8px"
      >
        {{ device.online ? '在线' : '离线' }}
      </el-tag>
    </el-option>
  </el-select>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useDeviceStore } from '@/stores/device'

const props = withDefaults(defineProps<{
  modelValue?: string
  placeholder?: string
}>(), {
  modelValue: '',
  placeholder: '选择设备...',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'change': [deviceId: string]
}>()

const deviceStore = useDeviceStore()
const selectedId = ref(props.modelValue)

const devices = deviceStore.devices

watch(() => props.modelValue, (val) => {
  selectedId.value = val
})

onMounted(() => {
  deviceStore.refresh()
})

function handleChange(val: string) {
  emit('update:modelValue', val)
  emit('change', val)
}
</script>
