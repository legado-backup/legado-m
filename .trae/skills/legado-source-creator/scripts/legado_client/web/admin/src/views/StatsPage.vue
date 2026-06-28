<template>
  <div class="page-container">
    <h2>统计面板</h2>

    <!-- 概览卡片 -->
    <div class="overview-cards">
      <el-card shadow="hover" class="overview-card">
        <div class="card-inner">
          <el-icon :size="36" class="card-icon total"><Document /></el-icon>
          <div class="card-text">
            <div class="card-value">{{ overview.total }}</div>
            <div class="card-label">源总数</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="overview-card">
        <div class="card-inner">
          <div class="pass-ring" :style="{ '--percent': overview.passRate }">
            <span class="pass-rate-text">{{ overview.passRate }}%</span>
          </div>
          <div class="card-text">
            <div class="card-value">{{ overview.passRate }}%</div>
            <div class="card-label">通过率</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="overview-card">
        <div class="card-inner">
          <el-icon :size="36" class="card-icon book"><Reading /></el-icon>
          <div class="card-text">
            <div class="card-value">{{ overview.bookCount }}</div>
            <div class="card-label">书源数</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="overview-card">
        <div class="card-inner">
          <el-icon :size="36" class="card-icon rss"><Connection /></el-icon>
          <div class="card-text">
            <div class="card-value">{{ overview.rssCount }}</div>
            <div class="card-label">订阅源数</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 源类型切换 -->
    <div class="type-switch">
      <el-radio-group v-model="sourceType" @change="handleTypeChange">
        <el-radio-button label="all">全部</el-radio-button>
        <el-radio-button label="book">书源</el-radio-button>
        <el-radio-button label="rss">订阅源</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <el-card shadow="hover" class="chart-card">
        <template #header>
          <div class="chart-header">
            <span>测试结果分布</span>
            <el-button size="small" text @click="loadTestResult">刷新</el-button>
          </div>
        </template>
        <div ref="testResultChartRef" class="chart-container" />
      </el-card>

      <el-card shadow="hover" class="chart-card">
        <template #header>
          <div class="chart-header">
            <span>内容类型分布</span>
            <el-button size="small" text @click="loadContentType">刷新</el-button>
          </div>
        </template>
        <div ref="contentTypeChartRef" class="chart-container" />
      </el-card>
    </div>

    <div class="charts-row">
      <el-card shadow="hover" class="chart-card full-width">
        <template #header>
          <div class="chart-header">
            <span>分组分布 (Top 10)</span>
            <el-button size="small" text @click="loadGroupDist">刷新</el-button>
          </div>
        </template>
        <div ref="groupChartRef" class="chart-container" />
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Document, Reading, Connection } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { fetchStats, fetchTestResultStats, fetchGroupDistribution, fetchContentTypeDistribution } from '@/api/stats'

const sourceType = ref('all')

// 概览数据
const overview = ref({
  total: 0,
  passRate: 0,
  bookCount: 0,
  rssCount: 0,
})

// 图表 DOM 引用
const testResultChartRef = ref<HTMLDivElement>()
const contentTypeChartRef = ref<HTMLDivElement>()
const groupChartRef = ref<HTMLDivElement>()

// ECharts 实例
let testResultChart: echarts.ECharts | null = null
let contentTypeChart: echarts.ECharts | null = null
let groupChart: echarts.ECharts | null = null

async function loadOverview() {
  try {
    const res = await fetchStats()
    const data = res as any
    overview.value = {
      total: data.total ?? 0,
      passRate: data.pass_rate ?? data.passRate ?? 0,
      bookCount: data.book_count ?? data.bookCount ?? 0,
      rssCount: data.rss_count ?? data.rssCount ?? 0,
    }
  } catch { /* ignore */ }
}

async function loadTestResult() {
  if (!testResultChart) return
  try {
    const res = await fetchTestResultStats()
    const data = res as any
    const dist = data.test_result_distribution ?? data.testResultDistribution ?? {}
    const resultMap: Record<string, string> = {
      pass: '通过',
      fail: '失败',
      timeout: '超时',
      error: '错误',
      untested: '未测试',
    }
    const colorMap: Record<string, string> = {
      pass: '#67c23a',
      fail: '#f56c6c',
      timeout: '#e6a23c',
      error: '#909399',
      untested: '#c0c4cc',
    }
    const chartData = Object.entries(dist).map(([key, value]) => ({
      name: resultMap[key] || key,
      value: value as number,
      itemStyle: { color: colorMap[key] || '#909399' },
    }))
    testResultChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0, type: 'scroll' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: true,
        label: { show: true, formatter: '{b}\n{d}%' },
        data: chartData,
      }],
    })
  } catch { /* ignore */ }
}

async function loadContentType() {
  if (!contentTypeChart) return
  try {
    const res = await fetchContentTypeDistribution()
    const data = res as any
    const dist = data.items ?? data ?? []
    const typeNames: Record<number, string> = {
      0: '文本',
      1: '音频',
      2: '图片',
      3: '文件',
      4: '视频',
    }
    const chartData = Array.isArray(dist)
      ? dist.map((item: any) => ({
          name: typeNames[item.type ?? item.sourceType] ?? item.name ?? String(item.type ?? item.sourceType),
          value: item.count ?? item.value ?? 0,
        }))
      : Object.entries(dist).map(([key, value]) => ({
          name: typeNames[Number(key)] ?? key,
          value: value as number,
        }))
    contentTypeChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 80, right: 20, top: 10, bottom: 20 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: chartData.map((d: any) => d.name) },
      series: [{
        type: 'bar',
        data: chartData.map((d: any) => d.value),
        itemStyle: { color: '#409eff' },
        label: { show: true, position: 'right' },
      }],
    })
  } catch { /* ignore */ }
}

async function loadGroupDist() {
  if (!groupChart) return
  try {
    const res = await fetchGroupDistribution()
    const data = res as any
    const dist = data.items ?? data ?? []
    const items = Array.isArray(dist)
      ? dist.slice(0, 10).map((item: any) => ({ name: item.group ?? item.name, value: item.count ?? item.value ?? 0 }))
      : Object.entries(dist).slice(0, 10).map(([key, value]) => ({ name: key, value: value as number }))
    groupChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: 120, right: 20, top: 10, bottom: 20 },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: items.map(d => d.name) },
      series: [{
        type: 'bar',
        data: items.map(d => d.value),
        itemStyle: { color: '#e6a23c' },
        label: { show: true, position: 'right' },
      }],
    })
  } catch { /* ignore */ }
}

function handleTypeChange() {
  loadTestResult()
  loadContentType()
  loadGroupDist()
}

function handleResize() {
  testResultChart?.resize()
  contentTypeChart?.resize()
  groupChart?.resize()
}

onMounted(async () => {
  await loadOverview()
  await nextTick()
  // 初始化图表
  if (testResultChartRef.value) {
    testResultChart = echarts.init(testResultChartRef.value)
  }
  if (contentTypeChartRef.value) {
    contentTypeChart = echarts.init(contentTypeChartRef.value)
  }
  if (groupChartRef.value) {
    groupChart = echarts.init(groupChartRef.value)
  }
  // 加载图表数据
  loadTestResult()
  loadContentType()
  loadGroupDist()
  // 监听窗口 resize
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  testResultChart?.dispose()
  contentTypeChart?.dispose()
  groupChart?.dispose()
  testResultChart = null
  contentTypeChart = null
  groupChart = null
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 1000px) {
  .overview-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

.overview-card .card-inner {
  display: flex;
  align-items: center;
  gap: 16px;
}

.card-icon {
  flex-shrink: 0;
}

.card-icon.total { color: var(--el-color-primary); }
.card-icon.book { color: var(--el-color-success); }
.card-icon.rss { color: var(--el-color-warning); }

.pass-ring {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: conic-gradient(var(--el-color-success) calc(var(--percent) * 1%), var(--el-border-color-lighter) 0);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.pass-rate-text {
  font-size: 11px;
  font-weight: 600;
  color: var(--el-color-success);
}

.card-text {
  display: flex;
  flex-direction: column;
}

.card-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}

.card-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

.type-switch {
  margin-bottom: 20px;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.charts-row .full-width {
  grid-column: 1 / -1;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  height: 320px;
  width: 100%;
}

@media (max-width: 900px) {
  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>
