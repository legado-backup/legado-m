<template>
  <div class="page-container">
    <div class="page-header">
      <h2>真机管理</h2>
      <el-button type="primary" @click="showAddDialog">添加设备</el-button>
    </div>

    <!-- 设备卡片网格 -->
    <div v-loading="loading" class="device-grid">
      <el-card
        v-for="device in deviceList"
        :key="device.id"
        shadow="hover"
        class="device-card"
      >
        <template #header>
          <div class="card-header">
            <span class="device-name">{{ device.name }}</span>
            <el-tag v-if="device.isDefault" type="warning" size="small">默认</el-tag>
          </div>
        </template>
        <div class="card-body">
          <div class="device-info">
            <span class="info-label">地址：</span>
            <span>{{ device.address }}</span>
          </div>
          <div class="device-info">
            <span class="info-label">状态：</span>
            <span :class="['status-dot', device.online ? 'online' : 'offline']" />
            <span>{{ device.online ? '在线' : '离线' }}</span>
          </div>
          <div v-if="device.lastSeen" class="device-info">
            <span class="info-label">最后连接：</span>
            <span>{{ device.lastSeen }}</span>
          </div>
        </div>
        <div class="card-actions">
          <el-button size="small" @click="handleTestConnection(device)">测试连接</el-button>
          <el-button size="small" type="primary" @click="showPushDialog(device)">推送源</el-button>
          <el-button size="small" type="success" @click="showPullDialog(device)">拉取源</el-button>
          <el-button size="small" @click="showEditDialog(device)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(device)">删除</el-button>
        </div>
      </el-card>
      <el-empty v-if="!loading && deviceList.length === 0" description="暂无设备，点击右上角添加" />
    </div>

    <!-- 添加/编辑设备弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑设备' : '添加设备'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="deviceForm" :rules="formRules" ref="formRef" label-width="120px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="deviceForm.name" placeholder="设备名称" />
        </el-form-item>
        <el-form-item label="IP地址" prop="ip">
          <el-input v-model="deviceForm.ip" placeholder="例如 192.168.1.100" />
        </el-form-item>
        <el-form-item label="HTTP端口" prop="httpPort">
          <el-input-number v-model="deviceForm.httpPort" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item>
          <el-text type="info" size="small">
            WebSocket 端口 = HTTP 端口 + 1（Legado 源码硬编码）
          </el-text>
        </el-form-item>
        <el-form-item label="认证Token">
          <el-input v-model="deviceForm.token" placeholder="选填，大部分设备无需填写" />
          <div class="form-tip">大部分设备无需填写，为预留字段</div>
        </el-form-item>
        <el-form-item label="设为默认设备">
          <el-switch v-model="deviceForm.isDefault" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitDevice">确定</el-button>
      </template>
    </el-dialog>

    <!-- 推送源弹窗 -->
    <el-dialog v-model="pushDialogVisible" title="推送源到设备" width="400px">
      <el-form label-width="80px">
        <el-form-item label="源类型">
          <el-radio-group v-model="pushSourceType">
            <el-radio-button label="book">书源</el-radio-button>
            <el-radio-button label="rss">订阅源</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pushDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="pushing" @click="handlePush">推送</el-button>
      </template>
    </el-dialog>

    <!-- 拉取源弹窗 -->
    <el-dialog v-model="pullDialogVisible" title="从设备拉取源" width="400px">
      <el-form label-width="80px">
        <el-form-item label="源类型">
          <el-radio-group v-model="pullSourceType">
            <el-radio-button label="book">书源</el-radio-button>
            <el-radio-button label="rss">订阅源</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pullDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="pulling" @click="handlePull">拉取</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { fetchDevices, addDevice, updateDevice, deleteDevice, testDeviceConnection, pushSourcesToDevice, pullSourcesFromDevice } from '@/api/device'

interface DeviceRow {
  id: string
  name: string
  address: string
  online: boolean
  lastSeen?: string
  isDefault?: boolean
  ip?: string
  httpPort?: number
  token?: string
}

const loading = ref(false)
const deviceList = ref<DeviceRow[]>([])

// 添加/编辑弹窗
const dialogVisible = ref(false)
const isEdit = ref(false)
const editDeviceId = ref('')
const submitting = ref(false)
const formRef = ref<FormInstance>()

const deviceForm = ref({
  name: '',
  ip: '',
  httpPort: 1122,
  token: '',
  isDefault: false,
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  ip: [{ required: true, message: '请输入IP地址', trigger: 'blur' }],
  httpPort: [{ required: true, message: '请输入HTTP端口', trigger: 'blur' }],
}

// 推送源弹窗
const pushDialogVisible = ref(false)
const pushTargetDevice = ref<DeviceRow | null>(null)
const pushSourceType = ref('book')
const pushing = ref(false)

// 拉取源弹窗
const pullDialogVisible = ref(false)
const pullTargetDevice = ref<DeviceRow | null>(null)
const pullSourceType = ref('book')
const pulling = ref(false)

async function loadDevices() {
  loading.value = true
  try {
    const res = await fetchDevices()
    deviceList.value = (res as any) ?? []
  } catch {
    deviceList.value = []
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  isEdit.value = false
  editDeviceId.value = ''
  deviceForm.value = { name: '', ip: '', httpPort: 1122, token: '', isDefault: false }
  dialogVisible.value = true
}

function showEditDialog(device: DeviceRow) {
  isEdit.value = true
  editDeviceId.value = device.id
  const parts = device.address.split(':')
  deviceForm.value = {
    name: device.name,
    ip: parts[0] || '',
    httpPort: parts[1] ? parseInt(parts[1]) : 1122,
    token: device.token || '',
    isDefault: device.isDefault || false,
  }
  dialogVisible.value = true
}

async function handleSubmitDevice() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const address = `${deviceForm.value.ip}:${deviceForm.value.httpPort}`
    if (isEdit.value) {
      await updateDevice(editDeviceId.value, { name: deviceForm.value.name, address })
    } else {
      await addDevice({ name: deviceForm.value.name, address })
    }
    ElMessage.success(isEdit.value ? '设备已更新' : '设备已添加')
    dialogVisible.value = false
    await loadDevices()
  } catch (e: any) {
    ElMessage.error('操作失败: ' + (e.message || e))
  } finally {
    submitting.value = false
  }
}

async function handleTestConnection(device: DeviceRow) {
  try {
    const res = await testDeviceConnection(device.id)
    const data = res as any
    if (data.online || data.status === 'online') {
      ElMessage.success(`${device.name} 在线`)
    } else if (data.needAuth || data.status === 'need_auth') {
      ElMessage.warning(`${device.name} 在线，但需要认证`)
    } else {
      ElMessage.error(`${device.name} 离线`)
    }
  } catch {
    ElMessage.error(`${device.name} 连接测试失败`)
  }
}

function showPushDialog(device: DeviceRow) {
  pushTargetDevice.value = device
  pushSourceType.value = 'book'
  pushDialogVisible.value = true
}

async function handlePush() {
  if (!pushTargetDevice.value) return
  pushing.value = true
  try {
    await pushSourcesToDevice(pushTargetDevice.value.id, [])
    ElMessage.success('推送成功')
    pushDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error('推送失败: ' + (e.message || e))
  } finally {
    pushing.value = false
  }
}

function showPullDialog(device: DeviceRow) {
  pullTargetDevice.value = device
  pullSourceType.value = 'book'
  pullDialogVisible.value = true
}

async function handlePull() {
  if (!pullTargetDevice.value) return
  pulling.value = true
  try {
    await pullSourcesFromDevice(pullTargetDevice.value.id)
    ElMessage.success('拉取成功')
    pullDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error('拉取失败: ' + (e.message || e))
  } finally {
    pulling.value = false
  }
}

async function handleDelete(device: DeviceRow) {
  try {
    await ElMessageBox.confirm(`确定删除设备「${device.name}」？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteDevice(device.id)
    ElMessage.success('设备已删除')
    await loadDevices()
  } catch { /* 用户取消 */ }
}

onMounted(() => {
  loadDevices()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

@media (max-width: 1200px) {
  .device-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .device-grid {
    grid-template-columns: 1fr;
  }
}

.device-card {
  min-height: 200px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.device-name {
  font-weight: 600;
  font-size: 16px;
}

.card-body {
  margin-bottom: 12px;
}

.device-info {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 6px;
  font-size: 14px;
}

.info-label {
  color: var(--el-text-color-secondary);
  min-width: 80px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot.online {
  background-color: var(--el-color-success);
}

.status-dot.offline {
  background-color: var(--el-text-color-disabled);
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 12px;
}

.form-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
</style>
