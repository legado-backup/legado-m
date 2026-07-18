<template>
  <el-select
    v-model="selectedId"
    filterable
    remote
    reserve-keyword
    :placeholder="placeholder"
    :remote-method="handleSearch"
    :loading="searching"
    clearable
    @change="handleChange"
  >
    <el-option
      v-for="item in options"
      :key="item.id"
      :label="`${item.sourceName} (${item.sourceGroup || ''})`"
      :value="item.id"
    />
  </el-select>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { fetchSources } from '@/api/sources'

interface SourceOption {
  id: number
  sourceUrl: string
  sourceName: string
  sourceGroup: string
}

const props = withDefaults(defineProps<{
  modelValue?: number | string
  placeholder?: string
}>(), {
  modelValue: 0,
  placeholder: '搜索源...',
})

const emit = defineEmits<{
  'update:modelValue': [value: number]
  'change': [sourceId: number, source: SourceOption | undefined]
}>()

const selectedId = ref<number>(typeof props.modelValue === 'number' ? props.modelValue : 0)
const options = ref<SourceOption[]>([])
const searching = ref(false)

watch(() => props.modelValue, (val) => {
  selectedId.value = typeof val === 'number' ? val : parseInt(String(val)) || 0
})

async function handleSearch(query: string) {
  if (!query) {
    options.value = []
    return
  }
  searching.value = true
  try {
    const res = await fetchSources({ keyword: query, page: 1, page_size: 20 })
    const items = res.items ?? res ?? []
    options.value = items.map((i: any) => ({
      id: i.id,
      sourceUrl: i.source_url,
      sourceName: i.source_name,
      sourceGroup: i.source_group || '',
    }))
  } catch {
    options.value = []
  } finally {
    searching.value = false
  }
}

function handleChange(val: number) {
  emit('update:modelValue', val)
  const source = options.value.find(s => s.id === val)
  emit('change', val, source)
}
</script>
