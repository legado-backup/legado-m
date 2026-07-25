<template>
  <div class="source-detail-page" v-loading="loading">
    <!-- 顶栏 -->
    <div class="top-bar">
      <el-button @click="goBack" :icon="ArrowLeft">返回</el-button>
      <h2 class="source-title">{{ source.sourceName || '加载中...' }}</h2>
      <div class="top-actions">
        <el-button type="primary" @click="onTest" :loading="testLoading">测试</el-button>
        <el-button @click="onOptimize">优化</el-button>
        <el-button @click="onExport">导出</el-button>
        <DeviceSelect v-model="pushDeviceId" placeholder="推送设备" style="width: 180px" />
        <el-button @click="onPush" :disabled="!pushDeviceId">推送</el-button>
        <el-button type="danger" @click="onDelete">删除</el-button>
      </div>
    </div>

    <template v-if="!loading">
      <!-- 基本信息卡片 -->
      <el-card class="info-card" shadow="never">
        <template #header><span>基本信息</span></template>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="源URL">{{ source.sourceUrl || '-' }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag :type="source.sourceType === 0 ? 'primary' : 'success'" size="small">
              {{ source.sourceType === 0 ? '书源' : '订阅源' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="内容类型">{{ formatContentType(source) }}</el-descriptions-item>
          <el-descriptions-item label="分组">{{ source.sourceGroup || '-' }}</el-descriptions-item>
          <el-descriptions-item label="登录URL">{{ source.loginUrl || '-' }}</el-descriptions-item>
          <el-descriptions-item label="启用">
            <el-switch :model-value="source.enabled" size="small" @change="(val: boolean) => onToggle(val)" />
          </el-descriptions-item>
          <el-descriptions-item label="搜索URL" :span="3">{{ source.searchUrl || '-' }}</el-descriptions-item>
          <el-descriptions-item label="详情URL" :span="3">{{ source.bookUrl || (source.articleStyle ?? '-') }}</el-descriptions-item>
          <el-descriptions-item label="目录URL" :span="3">{{ source.tocUrl || '-' }}</el-descriptions-item>
          <el-descriptions-item label="正文URL" :span="3">{{ source.contentUrl || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 测试结果步骤条 -->
      <el-card class="steps-card" shadow="never">
        <template #header><span>测试结果</span></template>
        <el-steps :active="testStepActive" finish-status="success" align-center>
          <el-step title="搜索" :status="testStepStatus('search')" :description="testStepDesc('search')" />
          <el-step title="详情" :status="testStepStatus('detail')" :description="testStepDesc('detail')" />
          <el-step title="目录" :status="testStepStatus('toc')" :description="testStepDesc('toc')" />
          <el-step title="正文" :status="testStepStatus('content')" :description="testStepDesc('content')" />
        </el-steps>
      </el-card>

      <!-- Tab 区域 -->
      <el-tabs v-model="activeTab" class="detail-tabs">
        <!-- Tab1: JSON 编辑 -->
        <el-tab-pane label="JSON编辑" name="json">
          <div class="json-toolbar">
            <el-button size="small" @click="formatJson">格式化</el-button>
            <el-button size="small" type="primary" @click="saveJson" :loading="saveLoading">保存</el-button>
            <el-button size="small" @click="resetJson">重置</el-button>
          </div>
          <JsonEditor ref="jsonEditorRef" v-model="jsonContent" height="500px" />
        </el-tab-pane>

        <!-- Tab2: 测试历史 -->
        <el-tab-pane label="测试历史" name="history">
          <div v-if="debugHistory.length === 0" class="empty-text">暂无测试历史</div>
          <el-timeline v-else>
            <el-timeline-item
              v-for="(item, i) in debugHistory"
              :key="i"
              :timestamp="formatDate(item.timestamp || item.created_at)"
              placement="top"
              :type="item.success ? 'success' : 'danger'"
            >
              <el-card shadow="never" class="history-card">
                <p>状态: <el-tag :type="item.success ? 'success' : 'danger'" size="small">{{ item.success ? '通过' : '失败' }}</el-tag></p>
                <p v-if="item.message">消息: {{ item.message }}</p>
                <p v-if="item.phases">阶段: {{ item.phases }}</p>
                <p v-if="item.duration">耗时: {{ item.duration }}ms</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-tab-pane>

        <!-- Tab3: 同域名源 -->
        <el-tab-pane label="同域名源" name="domain">
          <el-table :data="domainSources" v-loading="domainLoading" stripe>
            <el-table-column prop="sourceName" label="名称" min-width="160">
              <template #default="{ row }">
                <el-link type="primary" @click="goDetail(row.sourceUrl)">{{ row.sourceName || '-' }}</el-link>
              </template>
            </el-table-column>
            <el-table-column prop="sourceUrl" label="URL" min-width="200" show-overflow-tooltip />
            <el-table-column label="类型" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.sourceType === 0 ? 'primary' : 'success'" size="small">
                  {{ row.sourceType === 0 ? '书源' : '订阅源' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="启用" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '是' : '否' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- Tab4: 真机 vs JAR 对比 -->
        <el-tab-pane label="真机vs JAR对比" name="compare">
          <div class="compare-wrap">
            <div v-if="!compareData" class="empty-text">暂无对比数据，请先执行测试</div>
            <el-table v-else :data="compareData" stripe border>
              <el-table-column prop="phase" label="阶段" width="120" />
              <el-table-column prop="jarResult" label="JAR结果" min-width="200">
                <template #default="{ row }">
                  <el-tag :type="row.jarPass ? 'success' : 'danger'" size="small">{{ row.jarResult }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="deviceResult" label="真机结果" min-width="200">
                <template #default="{ row }">
                  <el-tag :type="row.devicePass ? 'success' : 'danger'" size="small">{{ row.deviceResult }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="一致性" width="100" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.jarPass === row.devicePass ? 'success' : 'warning'" size="small">
                    {{ row.jarPass === row.devicePass ? '一致' : '不一致' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { fetchSource, fetchSources, deleteSource, updateSource, toggleSource, exportSource, fetchSourcesByDomain, validateSources } from '@/api/sources'
import { pushSourcesToDevice } from '@/api/device'
import JsonEditor from '@/components/JsonEditor.vue'
import DeviceSelect from '@/components/DeviceSelect.vue'

const route = useRoute()
const router = useRouter()
const sourceId = decodeURIComponent(route.params.id as string)

const loading = ref(true)
const source = ref<any>({})
const jsonContent = ref('{}')
const originalJson = ref('{}')
const activeTab = ref('json')
const saveLoading = ref(false)
const testLoading = ref(false)
const pushDeviceId = ref('')

const jsonEditorRef = ref<InstanceType<typeof JsonEditor>>()
const debugHistory = ref<any[]>([])
const domainSources = ref<any[]>([])
const domainLoading = ref(false)
const compareData = ref<any[] | null>(null)

// 测试步骤状态
const testResults = ref<Record<string, { status: 'wait' | 'process' | 'finish' | 'error'; desc: string }>>({})

onMounted(async () => {
  await loadSource()
})

async function loadSource() {
  loading.value = true
  try {
    const res = await fetchSource(sourceId)
    source.value = res
    const json = JSON.stringify(res, null, 2)
    jsonContent.value = json
    originalJson.value = json
    // 解析测试结果
    if (res.testResults) {
      testResults.value = res.testResults
    }
    if (res.debugHistory) {
      debugHistory.value = res.debugHistory
    }
  } catch (e: any) {
    ElMessage.error('加载源详情失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push({ name: 'SourceList' })
}

function goDetail(url: string) {
  router.push({ name: 'SourceDetail', params: { id: encodeURIComponent(url) } })
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

const testStepActive = computed(() => {
  const phases = ['search', 'detail', 'toc', 'content']
  for (let i = 0; i < phases.length; i++) {
    const s = testResults.value[phases[i]]?.status
    if (!s || s === 'wait') return i
  }
  return 4
})

function testStepStatus(phase: string): '' | 'wait' | 'process' | 'finish' | 'error' {
  const s = testResults.value[phase]?.status
  if (s === 'finish') return 'success' as any
  if (s === 'error') return 'error'
  if (s === 'process') return 'process'
  return 'wait'
}

function testStepDesc(phase: string): string {
  return testResults.value[phase]?.desc || ''
}

async function onTest() {
  testLoading.value = true
  try {
    await validateSources({ urls: [sourceId] })
    ElMessage.success('测试已启动')
    testResults.value = {
      search: { status: 'process', desc: '测试中...' },
      detail: { status: 'wait', desc: '' },
      toc: { status: 'wait', desc: '' },
      content: { status: 'wait', desc: '' },
    }
  } catch (e: any) {
    ElMessage.error('启动测试失败: ' + (e.message || e))
  } finally {
    testLoading.value = false
  }
}

function onOptimize() {
  ElMessage.info('优化功能开发中')
}

async function onExport() {
  try {
    const blob = await exportSource(sourceId) as any
    const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob]))
    const a = document.createElement('a')
    a.href = url
    a.download = `${source.value.sourceName || 'source'}_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e: any) {
    ElMessage.error('导出失败: ' + (e.message || e))
  }
}

async function onPush() {
  if (!pushDeviceId.value) return
  try {
    await pushSourcesToDevice(pushDeviceId.value, [sourceId])
    ElMessage.success('推送成功')
  } catch (e: any) {
    ElMessage.error('推送失败: ' + (e.message || e))
  }
}

async function onDelete() {
  try {
    await ElMessageBox.confirm(`确定删除源「${source.value.sourceName || sourceId}」？`, '删除确认', { type: 'warning' })
    await deleteSource(sourceId)
    ElMessage.success('已删除')
    goBack()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('删除失败: ' + (e.message || e))
  }
}

async function onToggle(val: boolean) {
  try {
    await toggleSource(sourceId)
    source.value.enabled = val
    ElMessage.success(val ? '已启用' : '已禁用')
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e.message || e))
  }
}

function formatJson() {
  jsonEditorRef.value?.format()
}

async function saveJson() {
  saveLoading.value = true
  try {
    const data = JSON.parse(jsonContent.value)
    await updateSource(sourceId, data)
    source.value = data
    originalJson.value = jsonContent.value
    ElMessage.success('保存成功')
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.message || e))
  } finally {
    saveLoading.value = false
  }
}

function resetJson() {
  jsonContent.value = originalJson.value
}

// 加载同域名源（通过搜索同域名实现）
async function loadDomainSources() {
  domainLoading.value = true
  try {
    let domain = ''
    try {
      domain = new URL(source.value.sourceUrl).hostname
    } catch { domain = '' }
    if (!domain) { domainSources.value = []; return }
    const res = await fetchSourcesByDomain(domain)
    const list = (res as any).items ?? (res as any).data ?? res ?? []
    domainSources.value = Array.isArray(list) ? list.filter((s: any) => s.sourceUrl !== sourceId) : []
  } catch {
    domainSources.value = []
  } finally {
    domainLoading.value = false
  }
}

// 切换Tab时懒加载
watch(activeTab, (tab) => {
  if (tab === 'domain' && domainSources.value.length === 0) {
    loadDomainSources()
  }
})
</script>

<style scoped>
.source-detail-page {
  padding: 16px;
}

.top-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.source-title {
  flex: 1;
  margin: 0;
  font-size: 18px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.info-card {
  margin-bottom: 16px;
}

.steps-card {
  margin-bottom: 16px;
}

.detail-tabs {
  margin-top: 8px;
}

.json-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.empty-text {
  text-align: center;
  color: var(--el-text-color-placeholder);
  padding: 32px 0;
}

.history-card {
  font-size: 13px;
}

.history-card p {
  margin: 4px 0;
}

.compare-wrap {
  padding: 8px 0;
}
</style>
