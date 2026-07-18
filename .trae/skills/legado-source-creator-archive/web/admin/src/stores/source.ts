import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface SourceItem {
  sourceUrl: string
  sourceName: string
  sourceGroup: string
  sourceType: number
  enabled: boolean
  lastCheck?: string
  [key: string]: any
}

export const useSourceStore = defineStore('source', () => {
  // 源列表
  const sources = ref<SourceItem[]>([])
  // 筛选
  const filter = ref({
    keyword: '',
    group: '',
    type: null as number | null,
    enabled: null as boolean | null,
  })
  // 分页
  const page = ref(1)
  const pageSize = ref(20)
  const total = ref(0)
  // 选中项
  const selectedUrls = ref<Set<string>>(new Set())
  // 加载状态
  const loading = ref(false)

  // 计算属性：筛选后的源列表
  const filteredSources = computed(() => {
    let list = sources.value
    if (filter.value.keyword) {
      const kw = filter.value.keyword.toLowerCase()
      list = list.filter(s =>
        s.sourceName.toLowerCase().includes(kw) ||
        s.sourceUrl.toLowerCase().includes(kw) ||
        s.sourceGroup.toLowerCase().includes(kw)
      )
    }
    if (filter.value.group) {
      list = list.filter(s => s.sourceGroup === filter.value.group)
    }
    if (filter.value.type !== null) {
      list = list.filter(s => s.sourceType === filter.value.type)
    }
    if (filter.value.enabled !== null) {
      list = list.filter(s => s.enabled === filter.value.enabled)
    }
    return list
  })

  // 计算属性：分页后的源列表
  const pagedSources = computed(() => {
    const start = (page.value - 1) * pageSize.value
    return filteredSources.value.slice(start, start + pageSize.value)
  })

  function toggleSelect(url: string) {
    if (selectedUrls.value.has(url)) {
      selectedUrls.value.delete(url)
    } else {
      selectedUrls.value.add(url)
    }
  }

  function selectAll() {
    filteredSources.value.forEach(s => selectedUrls.value.add(s.sourceUrl))
  }

  function clearSelection() {
    selectedUrls.value.clear()
  }

  return {
    sources, filter, page, pageSize, total, selectedUrls, loading,
    filteredSources, pagedSources,
    toggleSelect, selectAll, clearSelection,
  }
})
