<template>
  <div class="import-page">
    <div class="import-grid">
      <!-- URL导入 -->
      <el-card shadow="never" class="import-card">
        <template #header>
          <div class="card-header">
            <el-icon><Link /></el-icon>
            <span>URL 导入</span>
          </div>
        </template>
        <el-input
          v-model="urlInput"
          placeholder="输入源 JSON 文件 URL"
          clearable
          style="margin-bottom: 12px"
        />
        <div class="card-footer">
          <el-select v-model="urlType" style="width: 120px; margin-right: 8px">
            <el-option label="自动检测" value="auto" />
            <el-option label="书源" value="book" />
            <el-option label="订阅源" value="rss" />
          </el-select>
          <el-button type="primary" @click="onImportUrl" :loading="urlLoading" :disabled="!urlInput">导入</el-button>
        </div>
      </el-card>

      <!-- 文件上传 -->
      <el-card shadow="never" class="import-card">
        <template #header>
          <div class="card-header">
            <el-icon><Upload /></el-icon>
            <span>文件上传</span>
          </div>
        </template>
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          :on-change="onFileChange"
          :on-exceed="() => ElMessage.warning('只能上传一个文件')"
          accept=".json,.txt"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">拖拽文件到此处，或<em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 .json / .txt 格式的源文件</div>
          </template>
        </el-upload>
        <div class="card-footer" style="margin-top: 12px">
          <el-select v-model="fileType" style="width: 120px; margin-right: 8px">
            <el-option label="自动检测" value="auto" />
            <el-option label="书源" value="book" />
            <el-option label="订阅源" value="rss" />
          </el-select>
          <el-button type="primary" @click="onImportFile" :loading="fileLoading" :disabled="!selectedFile">导入</el-button>
        </div>
      </el-card>

      <!-- GitHub导入 -->
      <el-card shadow="never" class="import-card">
        <template #header>
          <div class="card-header">
            <el-icon><Connection /></el-icon>
            <span>GitHub 导入</span>
          </div>
        </template>
        <el-input
          v-model="githubUrl"
          placeholder="输入 GitHub 仓库 URL 或 Raw 文件链接"
          clearable
          style="margin-bottom: 12px"
        />
        <div class="card-footer">
          <el-button type="primary" @click="onImportGithub" :loading="githubLoading" :disabled="!githubUrl">导入</el-button>
        </div>
      </el-card>

      <!-- 真机拉取 -->
      <el-card shadow="never" class="import-card">
        <template #header>
          <div class="card-header">
            <el-icon><Iphone /></el-icon>
            <span>真机拉取</span>
          </div>
        </template>
        <DeviceSelect v-model="pullDeviceId" placeholder="选择 Legado 设备" style="width: 100%; margin-bottom: 12px" />
        <div class="card-footer">
          <el-select v-model="pullType" style="width: 120px; margin-right: 8px">
            <el-option label="书源" value="book" />
            <el-option label="订阅源" value="rss" />
          </el-select>
          <el-button type="primary" @click="onPullFromDevice" :loading="pullLoading" :disabled="!pullDeviceId">拉取</el-button>
        </div>
      </el-card>
    </div>

    <!-- 导入结果统计 -->
    <el-card v-if="resultVisible" shadow="never" class="result-card">
      <template #header><span>导入结果</span></template>
      <ResultSummary
        :added="result.added"
        :skipped="result.skipped"
        :failed="result.failed"
        :failed-items="result.failedItems"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Link, Upload, UploadFilled, Connection, Iphone } from '@element-plus/icons-vue'
import { importFromUrl, importFromFile, importFromGithub, importFromLegadoPull } from '@/api/import'
import DeviceSelect from '@/components/DeviceSelect.vue'
import ResultSummary from '@/components/ResultSummary.vue'

// URL 导入
const urlInput = ref('')
const urlType = ref('auto')
const urlLoading = ref(false)

// 文件上传
const uploadRef = ref()
const selectedFile = ref<File | null>(null)
const fileType = ref('auto')
const fileLoading = ref(false)

// GitHub 导入
const githubUrl = ref('')
const githubLoading = ref(false)

// 真机拉取
const pullDeviceId = ref('')
const pullType = ref('book')
const pullLoading = ref(false)

// 导入结果
const resultVisible = ref(false)
const result = reactive({
  added: 0,
  skipped: 0,
  failed: 0,
  failedItems: [] as string[],
})

function showResult(res: any) {
  result.added = res.added ?? res.inserted ?? 0
  result.skipped = res.skipped ?? res.duplicate ?? 0
  result.failed = res.failed ?? res.error ?? 0
  result.failedItems = res.failedItems ?? res.errors ?? []
  resultVisible.value = true
}

function handleImportError(e: any, label: string) {
  result.added = 0
  result.skipped = 0
  result.failed = 1
  result.failedItems = [`${label}: ${e.message || e}`]
  resultVisible.value = true
}

async function onImportUrl() {
  if (!urlInput.value) return
  urlLoading.value = true
  try {
    const res = await importFromUrl(urlInput.value)
    showResult(res)
    ElMessage.success('URL 导入完成')
  } catch (e: any) {
    handleImportError(e, 'URL导入')
    ElMessage.error('URL 导入失败')
  } finally {
    urlLoading.value = false
  }
}

function onFileChange(file: any) {
  selectedFile.value = file.raw ?? file
}

async function onImportFile() {
  if (!selectedFile.value) return
  fileLoading.value = true
  try {
    const res = await importFromFile(selectedFile.value)
    showResult(res)
    ElMessage.success('文件导入完成')
    uploadRef.value?.clearFiles()
    selectedFile.value = null
  } catch (e: any) {
    handleImportError(e, '文件导入')
    ElMessage.error('文件导入失败')
  } finally {
    fileLoading.value = false
  }
}

async function onImportGithub() {
  if (!githubUrl.value) return
  githubLoading.value = true
  try {
    const res = await importFromGithub(githubUrl.value)
    showResult(res)
    ElMessage.success('GitHub 导入完成')
  } catch (e: any) {
    handleImportError(e, 'GitHub导入')
    ElMessage.error('GitHub 导入失败')
  } finally {
    githubLoading.value = false
  }
}

async function onPullFromDevice() {
  if (!pullDeviceId.value) return
  pullLoading.value = true
  try {
    const res = await importFromLegadoPull({ device_id: pullDeviceId.value, source_type: pullType.value })
    showResult(res)
    ElMessage.success('真机拉取完成')
  } catch (e: any) {
    handleImportError(e, '真机拉取')
    ElMessage.error('真机拉取失败')
  } finally {
    pullLoading.value = false
  }
}
</script>

<style scoped>
.import-page {
  padding: 16px;
}

.import-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 900px) {
  .import-grid {
    grid-template-columns: 1fr;
  }
}

.import-card {
  min-height: 240px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.result-card {
  margin-top: 16px;
}
</style>
