<template>
  <div class="result-summary">
    <el-descriptions :column="3" border size="small">
      <el-descriptions-item label="新增">
        <el-tag type="success" effect="dark">{{ added }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="跳过">
        <el-tag type="warning" effect="dark">{{ skipped }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="失败">
        <el-tag type="danger" effect="dark">{{ failed }}</el-tag>
      </el-descriptions-item>
    </el-descriptions>
    <div v-if="total > 0" class="result-bar">
      <div class="result-bar-inner">
        <div class="bar-added" :style="{ width: `${addedPercent}%` }" />
        <div class="bar-skipped" :style="{ width: `${skippedPercent}%` }" />
        <div class="bar-failed" :style="{ width: `${failedPercent}%` }" />
      </div>
    </div>
    <div v-if="failedItems.length > 0" class="failed-details">
      <el-collapse>
        <el-collapse-item :title="`失败详情 (${failedItems.length})`">
          <ul class="failed-list">
            <li v-for="(item, i) in failedItems" :key="i">{{ item }}</li>
          </ul>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  added?: number
  skipped?: number
  failed?: number
  failedItems?: string[]
}>(), {
  added: 0,
  skipped: 0,
  failed: 0,
  failedItems: () => [],
})

const total = computed(() => props.added + props.skipped + props.failed)

const addedPercent = computed(() => total.value ? (props.added / total.value * 100) : 0)
const skippedPercent = computed(() => total.value ? (props.skipped / total.value * 100) : 0)
const failedPercent = computed(() => total.value ? (props.failed / total.value * 100) : 0)
</script>

<style scoped>
.result-summary {
  width: 100%;
}

.result-bar {
  margin-top: 8px;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--el-fill-color-light);
}

.result-bar-inner {
  display: flex;
  height: 100%;
}

.bar-added {
  background: var(--el-color-success);
  transition: width 0.3s;
}

.bar-skipped {
  background: var(--el-color-warning);
  transition: width 0.3s;
}

.bar-failed {
  background: var(--el-color-danger);
  transition: width 0.3s;
}

.failed-details {
  margin-top: 8px;
}

.failed-list {
  margin: 0;
  padding-left: 20px;
  font-size: 12px;
  color: var(--el-color-danger);
}
</style>
