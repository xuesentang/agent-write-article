<script setup lang="ts">
/**
 * 历史记录页面
 * 展示所有创作过的文章，支持分页、筛选、搜索
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  HistoryOutlined,
  FileTextOutlined,
  DeleteOutlined,
  EyeOutlined,
  SearchOutlined,
  ReloadOutlined,
  CalendarOutlined,
  EditOutlined,
  PictureOutlined,
} from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

import { getArticles, deleteArticle, type ArticleResponse } from '@/api'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

// ============ 状态 ============

const router = useRouter()

// 文章列表
const articles = ref<ArticleResponse[]>([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

// 搜索
const searchKeyword = ref('')

// ============ 计算属性 ============

const filteredArticles = computed(() => {
  if (!searchKeyword.value.trim()) {
    return articles.value
  }
  const keyword = searchKeyword.value.toLowerCase()
  return articles.value.filter(
    article =>
      article.selected_title?.toLowerCase().includes(keyword) ||
      article.content?.toLowerCase().includes(keyword)
  )
})

// ============ 表格配置 ============

const columns = [
  {
    title: '标题',
    dataIndex: 'selected_title',
    key: 'title',
    ellipsis: true,
    width: 300,
  },
  {
    title: '字数',
    dataIndex: 'word_count',
    key: 'word_count',
    width: 100,
    align: 'center',
  },
  {
    title: '配图',
    dataIndex: 'images',
    key: 'images',
    width: 100,
    align: 'center',
  },
  {
    title: '创建时间',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 180,
  },
  {
    title: '操作',
    key: 'action',
    width: 160,
    align: 'center',
  },
]

// ============ 方法 ============

// 获取文章列表
async function fetchArticles() {
  loading.value = true
  try {
    const res = await getArticles({
      page: page.value,
      page_size: pageSize.value,
    })
    articles.value = res.data.items
    total.value = res.data.total
  } catch (err: any) {
    message.error(err.message || '获取列表失败')
  } finally {
    loading.value = false
  }
}

// 查看文章
function viewArticle(record: ArticleResponse) {
  router.push({ name: 'result', params: { id: record.id } })
}

// 删除文章
async function handleDelete(record: ArticleResponse) {
  if (!confirm(`确定要删除文章《${record.selected_title}》吗？`)) {
    return
  }

  try {
    await deleteArticle(record.id)
    message.success('删除成功')
    await fetchArticles()
  } catch (err: any) {
    message.error(err.message || '删除失败')
  }
}

// 分页变化
function handlePageChange(newPage: number, newPageSize: number) {
  page.value = newPage
  pageSize.value = newPageSize
  fetchArticles()
}

// 刷新列表
function refresh() {
  fetchArticles()
}

// 搜索
function handleSearch() {
  // 搜索是基于当前列表的客户端过滤
}

// 格式化时间
function formatTime(time: string): string {
  return dayjs(time).fromNow()
}

// 获取完整日期时间
function formatFullTime(time: string): string {
  return dayjs(time).format('YYYY-MM-DD HH:mm')
}

// ============ 生命周期 ============

onMounted(() => {
  fetchArticles()
})
</script>

<template>
  <div class="history-page">
    <!-- 页面头部 -->
    <div class="page-header glass-card">
      <div class="header-left">
        <h1 class="page-title">
          <HistoryOutlined class="title-icon" />
          历史记录
        </h1>
        <p class="page-subtitle">查看和管理您创作的所有文章</p>
      </div>
      <div class="header-right">
        <a-space>
          <a-input-search
            v-model:value="searchKeyword"
            placeholder="搜索文章标题..."
            style="width: 240px"
            @search="handleSearch"
          >
            <template #prefix><SearchOutlined /></template>
          </a-input-search>
          <a-button @click="refresh" :loading="loading">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
        </a-space>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card glass-card">
        <FileTextOutlined class="stat-icon" />
        <div class="stat-content">
          <span class="stat-value">{{ total }}</span>
          <span class="stat-label">篇文章</span>
        </div>
      </div>
      <div class="stat-card glass-card">
        <EditOutlined class="stat-icon" />
        <div class="stat-content">
          <span class="stat-value">
            {{ articles.reduce((sum, a) => sum + parseInt(a.word_count || '0'), 0).toLocaleString() }}
          </span>
          <span class="stat-label">总字数</span>
        </div>
      </div>
      <div class="stat-card glass-card">
        <PictureOutlined class="stat-icon" />
        <div class="stat-content">
          <span class="stat-value">
            {{ articles.reduce((sum, a) => sum + (a.images?.length || 0), 0) }}
          </span>
          <span class="stat-label">张配图</span>
        </div>
      </div>
    </div>

    <!-- 文章列表 -->
    <div class="list-section">
      <a-card class="list-card" :bordered="false">
        <a-table
          :columns="columns"
          :data-source="filteredArticles"
          :loading="loading"
          :pagination="{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total: number) => `共 ${total} 篇文章`,
          }"
          row-key="id"
          @change="(p: any) => handlePageChange(p.current, p.pageSize)"
        >
          <!-- 标题列 -->
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'title'">
              <div class="title-cell">
                <span class="title-text">{{ record.selected_title || '未命名文章' }}</span>
                <span v-if="record.title_options && record.title_options.length > 1" class="title-badge">
                  +{{ record.title_options.length - 1 }} 个备选
                </span>
              </div>
            </template>

            <!-- 字数列 -->
            <template v-else-if="column.key === 'word_count'">
              <span class="word-count">
                {{ parseInt(record.word_count || '0').toLocaleString() }}
              </span>
            </template>

            <!-- 配图列 -->
            <template v-else-if="column.key === 'images'">
              <a-badge :count="record.images?.length || 0" :number-style="{ backgroundColor: 'var(--primary-color)' }">
                <PictureOutlined class="image-icon" />
              </a-badge>
            </template>

            <!-- 时间列 -->
            <template v-else-if="column.key === 'created_at'">
              <a-tooltip :title="formatFullTime(record.created_at)">
                <span class="time-text">
                  <CalendarOutlined class="time-icon" />
                  {{ formatTime(record.created_at) }}
                </span>
              </a-tooltip>
            </template>

            <!-- 操作列 -->
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button type="link" size="small" @click="viewArticle(record)">
                  <EyeOutlined />
                  查看
                </a-button>
                <a-popconfirm
                  title="确定要删除这篇文章吗？"
                  ok-text="删除"
                  cancel-text="取消"
                  @confirm="handleDelete(record)"
                >
                  <a-button type="link" size="small" danger>
                    <DeleteOutlined />
                    删除
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-card>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && articles.length === 0" class="empty-section">
      <a-empty description="暂无文章记录">
        <a-button type="primary" @click="router.push({ name: 'create' })">
          开始创作第一篇文章
        </a-button>
      </a-empty>
    </div>
  </div>
</template>

<style scoped>
.history-page {
  padding: 0;
}

/* 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  margin-bottom: 24px;
}

.header-left {
  flex: 1;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.title-icon {
  margin-right: 12px;
  color: var(--primary-color);
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
}

.stat-icon {
  font-size: 32px;
  color: var(--primary-color);
  opacity: 0.8;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

/* 列表区域 */
.list-section {
  margin-bottom: 24px;
}

.list-card {
  overflow: hidden;
}

/* 标题单元格 */
.title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-text {
  font-weight: 500;
  color: var(--text-primary);
}

.title-badge {
  font-size: 11px;
  padding: 2px 6px;
  background: rgba(8, 145, 178, 0.1);
  color: var(--primary-color);
  border-radius: 4px;
}

/* 字数 */
.word-count {
  font-weight: 500;
  color: var(--text-secondary);
}

/* 图片图标 */
.image-icon {
  font-size: 20px;
  color: var(--text-muted);
}

/* 时间 */
.time-text {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.time-icon {
  color: var(--text-muted);
}

/* 空状态 */
.empty-section {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}

/* 响应式 */
@media (max-width: 1024px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }

  .header-right {
    width: 100%;
  }

  .header-right :deep(.ant-space) {
    width: 100%;
    flex-direction: column;
  }

  .header-right :deep(.ant-input-search) {
    width: 100% !important;
  }

  .stats-row {
    grid-template-columns: 1fr;
  }

  .stat-card {
    padding: 16px 20px;
  }
}
</style>