<template>
  <div class="collection-page">
    <!-- 类型切换 -->
    <div class="page-header">
      <el-tabs v-model="sourceType" @tab-change="onTypeChange">
        <el-tab-pane label="书源" name="book" />
        <el-tab-pane label="订阅源" name="rss" />
      </el-tabs>
      <div class="global-actions">
        <el-button type="primary" @click="onFetchRemote" :loading="remoteLoading">获取远程列表</el-button>
        <el-button @click="onFetchAll" :loading="fetchLoading">全量获取</el-button>
        <el-button @click="onIncrementalUpdate" :loading="updateLoading">增量更新</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table :data="collections" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column prop="userName" label="用户" width="120" />
      <el-table-column label="源数量" width="90" align="center">
        <template #default="{ row }">
          <el-tag size="small">{{ row.sourceCount ?? row.source_count ?? 0 }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="下载量" width="90" align="center">
        <template #default="{ row }">
          {{ row.downloadCount ?? row.download_count ?? 0 }}
        </template>
      </el-table-column>
      <el-table-column label="日期" width="160" align="center">
        <template #default="{ row }">
          {{ formatDate(row.updatedAt ?? row.updated_at ?? row.date) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'downloaded'" type="success" size="small">已下载</el-tag>
          <el-tag v-else-if="row.status === 'updating'" type="warning" size="small">更新中</el-tag>
          <el-tag v-else-if="row.status === 'error'" type="danger" size="small">失败</el-tag>
          <el-tag v-else type="info" size="small">未下载</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" align="center" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status !== 'downloaded'" size="small" link type="primary" @click="onDownload(row)">下载</el-button>
          <el-button v-if="row.status === 'downloaded'" size="small" link type="primary" @click="onUpdate(row)">更新</el-button>
          <el-button v-if="row.status === 'downloaded'" size="small" link type="danger" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadCollections"
        @current-change="loadCollections"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchCollections, fetchRemoteCollections, fetchAllCollections, incrementalUpdateCollections, downloadCollection, deleteCollection } from '@/api/collections'

const sourceType = ref('book')
const collections = ref<any[]>([])
const loading = ref(false)
const remoteLoading = ref(false)
const fetchLoading = ref(false)
const updateLoading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

onMounted(() => {
  loadCollections()
})

async function loadCollections() {
  loading.value = true
  try {
    const params: any = {
      page: page.value,
      page_size: pageSize.value,
      type: sourceType.value,
    }
    const res = await fetchCollections(params)
    collections.value = res.items ?? res.data ?? res ?? []
    total.value = res.total ?? collections.value.length
  } catch (e: any) {
    ElMessage.error('加载合集列表失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

function onTypeChange() {
  page.value = 1
  loadCollections()
}

function formatDate(ts: string): string {
  if (!ts) return '-'
  try {
    return new Date(ts).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return ts
  }
}

async function onFetchRemote() {
  remoteLoading.value = true
  try {
    ElMessage.info('正在获取远程列表...')
    const res = await fetchRemoteCollections({ type: sourceType.value })
    const data = res as any
    collections.value = data.items ?? data.data ?? data ?? []
    total.value = data.total ?? collections.value.length
    ElMessage.success('远程列表获取完成')
  } catch (e: any) {
    ElMessage.error('获取远程列表失败: ' + (e.message || e))
  } finally {
    remoteLoading.value = false
  }
}

async function onFetchAll() {
  try {
    await ElMessageBox.confirm(
      '全量获取将下载所有远程合集，可能耗时较长，确定继续？',
      '全量获取确认',
      { type: 'warning' }
    )
  } catch {
    return
  }
  fetchLoading.value = true
  try {
    await fetchAllCollections({ type: sourceType.value })
    ElMessage.success('全量获取完成')
    loadCollections()
  } catch (e: any) {
    ElMessage.error('全量获取失败: ' + (e.message || e))
  } finally {
    fetchLoading.value = false
  }
}

async function onIncrementalUpdate() {
  updateLoading.value = true
  try {
    await incrementalUpdateCollections({ type: sourceType.value })
    ElMessage.success('增量更新完成')
    loadCollections()
  } catch (e: any) {
    ElMessage.error('增量更新失败: ' + (e.message || e))
  } finally {
    updateLoading.value = false
  }
}

async function onDownload(row: any) {
  try {
    const id = row.id ?? row._id ?? row.collectionId
    if (!id) {
      ElMessage.warning('无合集ID')
      return
    }
    await downloadCollection(id)
    row.status = 'downloaded'
    ElMessage.success('下载成功')
  } catch (e: any) {
    row.status = 'error'
    ElMessage.error('下载失败: ' + (e.message || e))
  }
}

async function onUpdate(row: any) {
  try {
    const id = row.id ?? row._id ?? row.collectionId
    if (!id) {
      ElMessage.warning('无合集ID')
      return
    }
    row.status = 'updating'
    await downloadCollection(id)
    row.status = 'downloaded'
    ElMessage.success('更新成功')
  } catch (e: any) {
    row.status = 'error'
    ElMessage.error('更新失败: ' + (e.message || e))
  }
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除合集「${row.title}」？`, '删除确认', { type: 'warning' })
    const id = row.id ?? row._id ?? row.sourceUrl
    await deleteCollection(id)
    ElMessage.success('已删除')
    loadCollections()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('删除失败: ' + (e.message || e))
  }
}
</script>

<style scoped>
.collection-page {
  padding: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.page-header :deep(.el-tabs) {
  flex: 1;
}

.global-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
