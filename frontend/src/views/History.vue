<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// TODO: 从后端获取历史文章列表
const articles = ref([
  { id: '1', title: '如何在30天内打造爆款自媒体账号', createdAt: '2024-01-01', status: 'completed' },
  { id: '2', title: '自媒体新人必看：快速涨粉秘籍', createdAt: '2024-01-02', status: 'completed' },
])

const columns = [
  { title: '标题', dataIndex: 'title', key: 'title' },
  { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  { title: '操作', key: 'action' },
]

const handleView = (id: string) => {
  router.push({ name: 'result', params: { id } })
}
</script>

<template>
  <div class="history-container">
    <a-page-header title="历史记录" sub-title="查看您创建的所有文章" />

    <div class="table-section">
      <a-card>
        <a-table :columns="columns" :data-source="articles" row-key="id">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="record.status === 'completed' ? 'green' : 'blue'">
                {{ record.status === 'completed' ? '已完成' : '进行中' }}
              </a-tag>
            </template>
            <template v-if="column.key === 'action'">
              <a-button type="link" @click="handleView(record.id)">查看</a-button>
              <a-button type="link" danger>删除</a-button>
            </template>
          </template>
        </a-table>
      </a-card>
    </div>
  </div>
</template>

<style scoped>
.history-container {
  padding: 24px;
}

.table-section {
  max-width: 1000px;
  margin: 24px auto 0;
}
</style>