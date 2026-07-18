<template>
  <div class="page-container">
    <h2>批量校验</h2>

    <!-- 配置面板 -->
    <el-card class="config-card">
      <el-form :model="form" label-width="100px" class="validate-form">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="校验模式">
              <el-radio-group v-model="form.mode">
                <el-radio-button label="connectivity">连通性</el-radio-button>
                <el-radio-button label="jar">JAR仿真</el-radio-button>
                <el-radio-button label="device">真机</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="源类型">
              <el-radio-group v-model="form.sourceType">
                <el-radio-button label="book">书源</el-radio-button>
                <el-radio-button label="rss">订阅源</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item v-if="form.mode === 'device'" label="选择设备">
              <el-select v-model="form.deviceId" placeholder="选择设备" filterable>
                <el-option
                  v-for="d in devices"
                  :key="d.id"
                  :label="`${d.name} (${d.address})`"
                  :value="Number(d.id)"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="校验项目">
          <el-checkbox-group v-model="form.checks">
            <el-checkbox label="connectivity">连通性</el-checkbox>
            <el-checkbox label="search">搜索</el-checkbox>
            <el-checkbox label="detail">详情</el-checkbox>
            <el-checkbox label="toc">目录</el-checkbox>
            <el-checkbox label="content">正文</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="超时(秒)">
              <el-input-number v-model="form.timeout" :min="5" :max="300" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="并发数">
              <el-input-number v-model="form.maxConcurrent" :min="1" :max="10" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item>
          <el-button
            type="primary"
            :loading="running"
            :disabled="running"
            @click="handleStart"
          >
            {{ running ? '校验中...' : '开始校验' }}
          </el-button>
          <el-button
            v-if="running"
            type="danger"
            @click="handleStop"
          >
            停止校验
          </el-button>
          <el-button
            v-if="summary.dead > 0 && form.mode === 'device' && form.deviceId"
            type="warning"
            @click="handleCleanDead"
          >
            一键清理死源
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 一键清理死源面板 -->
    <el-card class="quick-clean-card">
      <template #header>
        <div class="quick-clean-header">
          <span>一键清理死源</span>
          <el-tag type="info" size="small">连通性检查 → 真机删除 → 数据库标记</el-tag>
        </div>
      </template>
      <el-row :gutter="16" align="middle">
        <el-col :span="6">
          <el-select v-model="quickClean.deviceId" placeholder="选择设备" filterable style="width: 100%">
            <el-option
              v-for="d in devices"
              :key="d.id"
              :label="`${d.name} (${d.address})`"
              :value="Number(d.id)"
            />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-radio-group v-model="quickClean.sourceType">
            <el-radio-button label="book">书源</el-radio-button>
            <el-radio-button label="rss">订阅源</el-radio-button>
          </el-radio-group>
        </el-col>
        <el-col :span="3">
          <el-checkbox v-model="quickClean.markDb">标记数据库</el-checkbox>
        </el-col>
        <el-col :span="4">
          <el-button
            type="danger"
            :loading="quickClean.loading"
            :disabled="quickClean.loading || !quickClean.deviceId"
            @click="handleQuickClean"
          >
            {{ quickClean.loading ? '清理中...' : '一键清理' }}
          </el-button>
        </el-col>
        <el-col :span="7">
          <div v-if="quickClean.result" class="quick-clean-result">
            <el-tag type="success" size="small">存活 {{ quickClean.result.alive }}</el-tag>
            <el-tag type="danger" size="small">死源 {{ quickClean.result.dead }}</el-tag>
            <el-tag type="warning" size="small" v-if="quickClean.result.deleted">已删 {{ quickClean.result.deleted }}</el-tag>
            <span class="quick-clean-time" v-if="quickClean.result.duration">
              耗时 {{ quickClean.result.duration }}s
            </span>
          </div>
        </el-col>
      </el-row>
      <el-progress
        v-if="quickClean.loading"
        :percentage="quickClean.progress"
        :stroke-width="14"
        style="margin-top: 12px"
      />
    </el-card>

    <!-- 进度条 -->
    <el-card v-if="running || progress > 0" class="progress-card">
      <el-progress
        :percentage="progress"
        :status="progress >= 100 ? 'success' : undefined"
        :stroke-width="20"
        :text-inside="true"
      />
      <p class="progress-text">
        已完成 {{ completed }} / {{ total }}
        <span v-if="running">（校验中...）</span>
        <span v-else>（已完成）</span>
      </p>
    </el-card>

    <!-- 统计摘要面板 -->
    <el-card v-if="summary.alive > 0 || summary.dead > 0" class="summary-card">
      <h4>统计摘要</h4>
      <el-row :gutter="16">
        <el-col :span="4">
          <el-statistic title="存活" :value="summary.alive">
            <template #suffix>
              <el-tag type="success" size="small">活</el-tag>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="4">
          <el-statistic title="死源" :value="summary.dead">
            <template #suffix>
              <el-tag type="danger" size="small">死</el-tag>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="4">
          <el-statistic title="搜索通过" :value="summary.search_pass" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="详情通过" :value="summary.detail_pass" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="目录通过" :value="summary.toc_pass" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="正文通过" :value="summary.content_pass" />
        </el-col>
      </el-row>
    </el-card>

    <!-- 结果列表 -->
    <el-card v-if="results.length > 0" class="results-card">
      <template #header>
        <div class="results-header">
          <span>校验结果</span>
          <el-input
            v-model="filterText"
            placeholder="搜索源名称/URL"
            clearable
            style="width: 300px"
            size="small"
          />
          <el-select v-model="filterStatus" size="small" style="width: 120px; margin-left: 8px">
            <el-option label="全部" value="all" />
            <el-option label="存活" value="pass" />
            <el-option label="死源" value="fail" />
          </el-select>
        </div>
      </template>
      <el-table :data="filteredResults" stripe max-height="500" size="small">
        <el-table-column prop="source_name" label="源名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="source_url" label="源地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="connectivity" label="连通性" width="80">
          <template #default="{ row }">
            <el-tag
              :type="row.connectivity === 'pass' ? 'success' : row.connectivity === 'fail' ? 'danger' : 'info'"
              size="small"
            >
              {{ row.connectivity === 'pass' ? '通过' : row.connectivity === 'fail' ? '失败' : '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="search" label="搜索" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.search !== 'skip'" :type="row.search === 'pass' ? 'success' : 'danger'" size="small">
              {{ row.search === 'pass' ? '通过' : '失败' }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.detail !== 'skip'" :type="row.detail === 'pass' ? 'success' : 'danger'" size="small">
              {{ row.detail === 'pass' ? '通过' : '失败' }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="toc" label="目录" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.toc !== 'skip'" :type="row.toc === 'pass' ? 'success' : 'danger'" size="small">
              {{ row.toc === 'pass' ? '通过' : '失败' }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="正文" width="70">
          <template #default="{ row }">
            <el-tag v-if="row.content !== 'skip'" :type="row.content === 'pass' ? 'success' : 'danger'" size="small">
              {{ row.content === 'pass' ? '通过' : '失败' }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="信息" min-width="160" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { batchValidate, batchValidateStatus } from '@/api/debug'
import { fetchDevices, cleanDeadSources } from '@/api/device'

const form = ref({
  mode: 'connectivity',
  sourceType: 'book',
  deviceId: undefined as number | undefined,
  checks: ['connectivity'] as string[],
  timeout: 30,
  maxConcurrent: 3,
})

const devices = ref<any[]>([])
const running = ref(false)
const taskId = ref('')
const total = ref(0)
const completed = ref(0)
const results = ref<any[]>([])
const summary = ref({
  alive: 0, dead: 0,
  search_pass: 0, detail_pass: 0,
  toc_pass: 0, content_pass: 0,
})
const filterText = ref('')
const filterStatus = ref('all')

const quickClean = ref({
  deviceId: undefined as number | undefined,
  sourceType: 'book',
  markDb: true,
  loading: false,
  progress: 0,
  result: null as { alive: number; dead: number; deleted?: number; duration?: number } | null,
})

let pollTimer: ReturnType<typeof setInterval> | null = null

const progress = computed(() => {
  if (total.value === 0) return 0
  return Math.round((completed.value / total.value) * 100)
})

const filteredResults = computed(() => {
  let list = results.value
  if (filterText.value) {
    const kw = filterText.value.toLowerCase()
    list = list.filter(
      (r) =>
        (r.source_name || '').toLowerCase().includes(kw) ||
        (r.source_url || '').toLowerCase().includes(kw),
    )
  }
  if (filterStatus.value !== 'all') {
    list = list.filter((r) => r.connectivity === filterStatus.value)
  }
  return list
})

async function handleStart() {
  if (form.value.mode === 'device' && !form.value.deviceId) {
    ElMessage.warning('请选择设备')
    return
  }

  running.value = true
  results.value = []
  completed.value = 0
  total.value = 0
  summary.value = { alive: 0, dead: 0, search_pass: 0, detail_pass: 0, toc_pass: 0, content_pass: 0 }

  try {
    const checkMap: Record<string, boolean> = {}
    for (const c of form.value.checks) {
      if (c === 'search') checkMap.check_search = true
      else if (c === 'detail') checkMap.check_detail = true
      else if (c === 'toc') checkMap.check_toc = true
      else if (c === 'content') checkMap.check_content = true
    }

    const res = await batchValidate({
      source_type: form.value.sourceType,
      mode: form.value.mode,
      device_id: form.value.deviceId,
      timeout: form.value.timeout,
      max_concurrent: form.value.maxConcurrent,
      ...checkMap,
    }) as any

    taskId.value = res.task_id || ''
    total.value = res.total || 0

    if (res.status === 'completed') {
      // 已经完成（无源）
      running.value = false
      results.value = res.results || []
      summary.value = res.summary || summary.value
      completed.value = total.value
    } else if (taskId.value) {
      startPoll()
    } else {
      running.value = false
    }
  } catch (e: any) {
    ElMessage.error('启动批量校验失败: ' + (e.message || e))
    running.value = false
  }
}

function startPoll() {
  stopPoll()
  pollTimer = setInterval(async () => {
    if (!taskId.value) return
    try {
      const res = await batchValidateStatus(taskId.value) as any
      total.value = res.total || 0
      completed.value = res.completed || 0
      results.value = res.results || []
      summary.value = res.summary || summary.value

      if (res.status === 'completed') {
        stopPoll()
        running.value = false
      }
    } catch {
      stopPoll()
      running.value = false
    }
  }, 2000)
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function handleStop() {
  stopPoll()
  running.value = false
  ElMessage.info('已停止轮询（后台任务仍在运行）')
}

async function handleCleanDead() {
  if (!form.value.deviceId) return

  try {
    await ElMessageBox.confirm(
      `确认清理设备上的 ${summary.value.dead} 个死源？此操作将删除设备上的死源并标记数据库。`,
      '清理死源',
      { confirmButtonText: '确认清理', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  try {
    const res = await cleanDeadSources(form.value.deviceId, {
      source_type: form.value.sourceType,
      dry_run: false,
      mark_db: true,
    }) as any
    const data = res.data || res
    ElMessage.success(`清理完成：删除 ${data.deleted || 0} 个死源`)
  } catch (e: any) {
    ElMessage.error('清理死源失败: ' + (e.message || e))
  }
}

async function handleQuickClean() {
  if (!quickClean.value.deviceId) {
    ElMessage.warning('请选择设备')
    return
  }

  const typeLabel = quickClean.value.sourceType === 'book' ? '书源' : '订阅源'
  try {
    await ElMessageBox.confirm(
      `确认一键清理真机上的死亡${typeLabel}？将执行：连通性检查 → 真机删除死源 → 数据库标记废弃`,
      '一键清理死源',
      { confirmButtonText: '确认清理', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  quickClean.value.loading = true
  quickClean.value.progress = 10
  quickClean.value.result = null
  const startTime = Date.now()

  try {
    // 1. 先做书源清理
    const res = await cleanDeadSources(quickClean.value.deviceId, {
      source_type: quickClean.value.sourceType,
      dry_run: false,
      mark_db: quickClean.value.markDb,
    }) as any

    quickClean.value.progress = 100
    const data = res.data || res
    const duration = ((Date.now() - startTime) / 1000).toFixed(1)
    quickClean.value.result = {
      alive: data.alive || 0,
      dead: data.dead || 0,
      deleted: data.deleted || 0,
      duration: Number(duration),
    }

    ElMessage.success(
      `${typeLabel}清理完成：存活 ${data.alive || 0}，删除 ${data.deleted || 0} 个死源，耗时 ${duration}s`,
    )
  } catch (e: any) {
    ElMessage.error('一键清理失败: ' + (e.message || e))
  } finally {
    quickClean.value.loading = false
  }
}

onMounted(async () => {
  try {
    const list = await fetchDevices()
    devices.value = list || []
  } catch { /* ignore */ }
})

onUnmounted(() => {
  stopPoll()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.config-card {
  margin-bottom: 16px;
}

.validate-form {
  max-width: 900px;
}

.progress-card {
  margin-bottom: 16px;
}

.progress-text {
  margin-top: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.summary-card {
  margin-bottom: 16px;
}

.summary-card h4 {
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
}

.results-card {
  margin-bottom: 16px;
}

.results-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.text-muted {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}

.quick-clean-card {
  margin-bottom: 16px;
}

.quick-clean-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quick-clean-result {
  display: flex;
  align-items: center;
  gap: 6px;
}

.quick-clean-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-left: 4px;
}
</style>
