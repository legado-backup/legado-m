<template>
  <div class="source-list-page">
    <!-- 搜索 + 筛选栏 -->
    <div class="toolbar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索源名称/URL/分组..."
        clearable
        style="width: 280px"
        @input="onSearchInput"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <div class="filters">
        <el-select v-model="filters.type" placeholder="类型" clearable style="width: 120px" @change="loadSources">
          <el-option label="书源" :value="0" />
          <el-option label="订阅源" :value="1" />
        </el-select>
        <el-select v-model="filters.contentType" placeholder="内容类型" clearable style="width: 130px" @change="loadSources">
          <el-option v-for="ct in contentTypeOptions" :key="ct.value" :label="ct.label" :value="ct.value" />
        </el-select>
        <el-select v-model="filters.testResult" placeholder="测试结果" clearable style="width: 120px" @change="loadSources">
          <el-option label="通过" value="pass" />
          <el-option label="失败" value="fail" />
          <el-option label="未测试" value="none" />
        </el-select>
        <el-select v-model="filters.group" placeholder="分组" clearable style="width: 130px" @change="loadSources">
          <el-option v-for="g in groupOptions" :key="g" :label="g" :value="g" />
        </el-select>
        <el-select v-model="filters.hasLogin" placeholder="有无登录" clearable style="width: 120px" @change="loadSources">
          <el-option label="有登录" :value="true" />
          <el-option label="无登录" :value="false" />
        </el-select>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedUrls.length > 0" class="batch-bar">
      <span>已选 {{ selectedUrls.length }} 项</span>
      <el-button size="small" type="primary" @click="onBatchTest" :loading="batchLoading">批量测试</el-button>
      <el-button size="small" @click="onBatchExport">导出</el-button>
      <el-button size="small" type="danger" @click="onBatchDelete">删除</el-button>
      <DeviceSelect v-model="pushDeviceId" placeholder="选择推送设备" style="width: 200px" />
      <el-button size="small" @click="onBatchPush" :disabled="!pushDeviceId">推送</el-button>
      <el-button size="small" @click="onBatchToggle(true)">启用</el-button>
      <el-button size="small" @click="onBatchToggle(false)">禁用</el-button>
    </div>

    <!-- 表格 -->
    <el-table
      :data="sourceList"
      v-loading="loading"
      @selection-change="onSelectionChange"
      stripe
      style="width: 100%"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column label="名称" min-width="180">
        <template #default="{ row }">
          <el-link type="primary" @click="goDetail(row.sourceUrl)">{{ row.sourceName || '-' }}</el-link>
        </template>
      </el-table-column>
      <el-table-column prop="sourceUrl" label="URL" min-width="200" show-overflow-tooltip />
      <el-table-column label="类型" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.sourceType === 0 ? 'primary' : 'success'" size="small">
            {{ row.sourceType === 0 ? '书源' : '订阅源' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="内容类型" width="90" align="center">
        <template #default="{ row }">
          {{ formatContentType(row) }}
        </template>
      </el-table-column>
      <el-table-column prop="sourceGroup" label="分组" width="100" show-overflow-tooltip />
      <el-table-column label="测试结果" width="90" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.testResult === 'pass'" type="success" size="small">通过</el-tag>
          <el-tag v-else-if="row.testResult === 'fail'" type="danger" size="small">失败</el-tag>
          <el-tag v-else type="info" size="small">未测试</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最后测试" width="160" align="center">
        <template #default="{ row }">
          {{ row.lastCheck ? formatDate(row.lastCheck) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="启用" width="70" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.enabled"
            size="small"
            @change="(val: boolean) => onToggleSource(row, val)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170" align="center" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="onTestOne(row)">测试</el-button>
          <el-button size="small" link @click="onCopyJson(row)">复制JSON</el-button>
          <el-button size="small" link type="danger" @click="onDeleteOne(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadSources"
        @current-change="loadSources"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { fetchSources, deleteSource, batchAction, fetchGroups, toggleSource, batchExport, validateSources } from '@/api/sources'
import { pushSourcesToDevice } from '@/api/device'
import DeviceSelect from '@/components/DeviceSelect.vue'

const router = useRouter()

// 列表数据
const sourceList = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

// 搜索
const searchKeyword = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

// 筛选器
const filters = reactive({
  type: null as number | null,
  contentType: null as number | null,
  testResult: '' as string,
  group: '',
  hasLogin: null as boolean | null,
})

const contentTypeOptions = [
  { label: '小说', value: 0 },
  { label: '漫画', value: 1 },
  { label: '有声', value: 2 },
  { label: '图片', value: 3 },
  { label: '文件', value: 4 },
]
const groupOptions = ref<string[]>([])

// 选中
const selectedUrls = ref<string[]>([])
const pushDeviceId = ref('')
const batchLoading = ref(false)

onMounted(async () => {
  await loadGroups()
  await loadSources()
})

async function loadSources() {
  loading.value = true
  try {
    const params: any = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (filters.type !== null) params.type = filters.type
    if (filters.group) params.group = filters.group
    if (filters.contentType !== null) params.content_type = filters.contentType
    if (filters.testResult) params.test_result = filters.testResult
    if (filters.hasLogin !== null) params.has_login = filters.hasLogin

    const res = await fetchSources(params)
    sourceList.value = res.items ?? res.data ?? res ?? []
    total.value = res.total ?? sourceList.value.length
  } catch (e: any) {
    ElMessage.error('加载源列表失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

async function loadGroups() {
  try {
    const res = await fetchGroups()
    groupOptions.value = Array.isArray(res) ? res : (res.groups ?? [])
  } catch {
    groupOptions.value = []
  }
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadSources()
  }, 300)
}

function resetFilters() {
  filters.type = null
  filters.contentType = null
  filters.testResult = ''
  filters.group = ''
  filters.hasLogin = null
  searchKeyword.value = ''
  page.value = 1
  loadSources()
}

function onSelectionChange(rows: any[]) {
  selectedUrls.value = rows.map(r => r.sourceUrl)
}

function goDetail(sourceUrl: string) {
  router.push({ name: 'SourceDetail', params: { id: encodeURIComponent(sourceUrl) } })
}

function formatContentType(row: any): string {
  if (row.sourceType === 0) {
    const map: Record<number, string> = { 0: '小说', 1: '漫画', 2: '有声', 3: '图片', 4: '文件' }
    return map[row.bookSourceType ?? row.book_source_type] ?? '-'
  }
  const map: Record<number, string> = { 0: '通用', 1: '音频', 2: '视频' }
  return map[row.rssType ?? row.rss_type] ?? '-'
}

function formatDate(ts: string): string {
  if (!ts) return '-'
  try {
    return new Date(ts).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return ts
  }
}

async function onToggleSource(row: any, val: boolean) {
  try {
    await toggleSource(row.sourceUrl)
    row.enabled = val
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e.message || e))
  }
}

async function onTestOne(row: any) {
  try {
    await validateSources({ urls: [row.sourceUrl] })
    ElMessage.success('已启动测试任务')
    row.testResult = 'testing'
    row.lastCheck = new Date().toISOString()
  } catch (e: any) {
    ElMessage.error('启动测试失败: ' + (e.message || e))
  }
}

async function onCopyJson(row: any) {
  try {
    const json = JSON.stringify(row, null, 2)
    await navigator.clipboard.writeText(json)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

async function onDeleteOne(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除源「${row.sourceName || row.sourceUrl}」？`, '删除确认', { type: 'warning' })
    await deleteSource(row.sourceUrl)
    ElMessage.success('已删除')
    loadSources()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('删除失败: ' + (e.message || e))
  }
}

async function onBatchTest() {
  if (selectedUrls.value.length === 0) return
  batchLoading.value = true
  try {
    await validateSources({ urls: selectedUrls.value })
    ElMessage.success(`已提交 ${selectedUrls.value.length} 个源的批量测试`)
  } catch (e: any) {
    ElMessage.error('批量测试失败: ' + (e.message || e))
  } finally {
    batchLoading.value = false
  }
}

async function onBatchExport() {
  if (selectedUrls.value.length === 0) return
  try {
    const blob = await batchExport({ urls: selectedUrls.value }) as any
    const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob]))
    const a = document.createElement('a')
    a.href = url
    a.download = `sources_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e: any) {
    ElMessage.error('导出失败: ' + (e.message || e))
  }
}

async function onBatchDelete() {
  if (selectedUrls.value.length === 0) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedUrls.value.length} 个源？`, '批量删除确认', { type: 'warning' })
    await batchAction({ action: 'delete', urls: selectedUrls.value })
    ElMessage.success('批量删除成功')
    loadSources()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('批量删除失败: ' + (e.message || e))
  }
}

async function onBatchPush() {
  if (!pushDeviceId.value || selectedUrls.value.length === 0) return
  try {
    await pushSourcesToDevice(pushDeviceId.value, selectedUrls.value)
    ElMessage.success(`已推送 ${selectedUrls.value.length} 个源到设备`)
  } catch (e: any) {
    ElMessage.error('推送失败: ' + (e.message || e))
  }
}

async function onBatchToggle(enabled: boolean) {
  if (selectedUrls.value.length === 0) return
  try {
    const action = enabled ? 'enable' : 'disable'
    await batchAction({ action, urls: selectedUrls.value })
    ElMessage.success(enabled ? '批量启用成功' : '批量禁用成功')
    loadSources()
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e.message || e))
  }
}
</script>

<style scoped>
.source-list-page {
  padding: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: var(--el-color-primary-light-9);
  border-radius: 4px;
  font-size: 14px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
