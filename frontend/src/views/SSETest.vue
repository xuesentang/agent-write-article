<script setup lang="ts">
/**
 * SSE 测试页面组件
 * 用于验证 SSE 通信是否正常
 */
import { ref, onUnmounted } from 'vue'
import { useSSE, SSEEventType, ConnectionState } from '@/composables/useSSE'

// 测试任务 ID
const testTaskId = ref('test-task-' + Date.now())

// SSE 相关状态
const {
  connectionState,
  lastError,
  eventCount,
  connect,
  disconnect,
  onAny,
} = useSSE(() => `/api/sse/test/${testTaskId.value}`, {
  maxReconnectAttempts: 3,
  reconnectDelay: 1000,
  autoReconnect: true,
})

// 测试结果
const testResults = ref<Array<{
  sequence: number
  event: string
  data: any
  timestamp: string
}>>([])

const testPassed = ref(false)
const testFailed = ref(false)
const isTesting = ref(false)

// 开始测试
const startTest = async () => {
  testResults.value = []
  testPassed.value = false
  testFailed.value = false
  isTesting.value = true

  // 注册事件回调
  onAny((data) => {
    testResults.value.push({
      sequence: data.sequence || testResults.value.length + 1,
      event: data.event,
      data: data.data,
      timestamp: data.timestamp || new Date().toISOString(),
    })

    // 检查是否收到完成事件
    if (data.event === SSEEventType.DONE) {
      if (data.data?.test_passed === true) {
        testPassed.value = true
      } else {
        testFailed.value = true
      }
      isTesting.value = false
    }
  })

  // 连接并接收事件
  try {
    await connect()
  } catch (error) {
    console.error('SSE 连接失败:', error)
    testFailed.value = true
    isTesting.value = false
  }
}

// 停止测试
const stopTest = () => {
  disconnect()
  isTesting.value = false
}

// 获取连接状态颜色
const getStateColor = (state: ConnectionState) => {
  switch (state) {
    case ConnectionState.CONNECTED:
      return 'green'
    case ConnectionState.CONNECTING:
      return 'blue'
    case ConnectionState.ERROR:
      return 'red'
    default:
      return 'default'
  }
}

// 获取事件类型颜色
const getEventColor = (event: string) => {
  switch (event) {
    case 'done':
      return 'green'
    case 'error':
      return 'red'
    case 'status':
      return 'blue'
    case 'progress':
      return 'orange'
    default:
      return 'default'
  }
}

// 清理
onUnmounted(() => {
  disconnect()
})
</script>

<template>
  <div class="sse-test-container">
    <a-card title="SSE 通信测试" class="test-card">
      <!-- 状态展示 -->
      <a-descriptions :column="3" bordered size="small">
        <a-descriptions-item label="连接状态">
          <a-tag :color="getStateColor(connectionState)">
            {{ connectionState }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="收到事件数">
          {{ eventCount }}
        </a-descriptions-item>
        <a-descriptions-item label="最后错误">
          <span v-if="lastError" class="error-text">{{ lastError }}</span>
          <span v-else class="success-text">无</span>
        </a-descriptions-item>
      </a-descriptions>

      <!-- 操作按钮 -->
      <div class="actions">
        <a-space>
          <a-input
            v-model:value="testTaskId"
            placeholder="任务 ID"
            style="width: 300px"
            :disabled="isTesting"
          />
          <a-button
            type="primary"
            @click="startTest"
            :disabled="isTesting"
            :loading="connectionState === ConnectionState.CONNECTING"
          >
            开始测试
          </a-button>
          <a-button @click="stopTest" :disabled="!isTesting">
            停止测试
          </a-button>
        </a-space>
      </div>

      <!-- 测试结果 -->
      <div class="result-section">
        <a-alert
          v-if="testPassed"
          type="success"
          show-icon
          class="result-alert"
        >
          <template #message>
            <strong>✅ SSE 测试通过！</strong>
          </template>
          <template #description>
            <p>成功收到 {{ testResults.length }} 条消息，最后一条消息包含 <code>test_passed: true</code></p>
          </template>
        </a-alert>

        <a-alert
          v-if="testFailed"
          type="error"
          show-icon
          class="result-alert"
        >
          <template #message>
            <strong>❌ SSE 测试失败</strong>
          </template>
          <template #description>
            <p>未能正确接收到完成事件，请检查网络连接和后端服务</p>
          </template>
        </a-alert>
      </div>

      <!-- 事件列表 -->
      <div class="events-section" v-if="testResults.length > 0">
        <h4>收到的事件 ({{ testResults.length }} 条)</h4>
        <a-table
          :dataSource="testResults"
          :columns="[
            { title: '#', dataIndex: 'sequence', width: 60 },
            { title: '事件类型', dataIndex: 'event', width: 150 },
            { title: '进度', dataIndex: 'data.progress', width: 80 },
            { title: '数据', dataIndex: 'data', ellipsis: true },
            { title: '时间', dataIndex: 'timestamp', width: 180 },
          ]"
          :pagination="false"
          size="small"
          rowKey="sequence"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'event'">
              <a-tag :color="getEventColor(record.event)">
                {{ record.event }}
              </a-tag>
            </template>
            <template v-if="column.dataIndex === 'data'">
              <code>{{ JSON.stringify(record.data, null, 0) }}</code>
            </template>
            <template v-if="column.dataIndex === 'data.progress'">
              <a-progress
                v-if="record.data?.progress !== undefined"
                :percent="record.data.progress"
                size="small"
                :showInfo="true"
              />
            </template>
          </template>
        </a-table>
      </div>

      <!-- 使用说明 -->
      <a-collapse class="instructions">
        <a-collapse-panel key="1" header="测试说明">
          <ol>
            <li>点击"开始测试"按钮，系统将建立 SSE 连接</li>
            <li>后端每秒推送一条模拟消息，共 10 条</li>
            <li><strong>测试正常的标志：</strong>
              <ul>
                <li>收到 10 条消息</li>
                <li>最后一条消息的事件类型为 <code>done</code></li>
                <li>最后一条消息的 data 包含 <code>test_passed: true</code></li>
              </ul>
            </li>
            <li>如果显示绿色的"✅ SSE 测试通过！"，说明通信正常</li>
          </ol>
        </a-collapse-panel>
      </a-collapse>
    </a-card>
  </div>
</template>

<style scoped>
.sse-test-container {
  padding: 24px;
}

.test-card {
  max-width: 1000px;
  margin: 0 auto;
}

.actions {
  margin: 24px 0;
}

.result-section {
  margin: 16px 0;
}

.result-alert {
  margin-bottom: 16px;
}

.events-section {
  margin-top: 24px;
}

.events-section h4 {
  margin-bottom: 12px;
}

.error-text {
  color: #ff4d4f;
}

.success-text {
  color: #52c41a;
}

.instructions {
  margin-top: 24px;
}

.instructions ol,
.instructions ul {
  padding-left: 20px;
}

.instructions li {
  margin: 8px 0;
}

code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}
</style>