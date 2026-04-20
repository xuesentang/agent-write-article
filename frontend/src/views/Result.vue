<script setup lang="ts">
/**
 * 文章结果展示页
 * 显示完整的文章内容、配图、提供导出功能
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  FileTextOutlined,
  DownloadOutlined,
  CopyOutlined,
  DeleteOutlined,
  ShareAltOutlined,
  PictureOutlined,
  EditOutlined,
  ArrowLeftOutlined,
  CheckOutlined,
} from '@ant-design/icons-vue'
import MarkdownIt from 'markdown-it'

import { getArticle, exportArticle, deleteArticle, type ArticleResponse, type ImageInfo } from '@/api'

// ============ 初始化 ============

const route = useRoute()
const router = useRouter()

const articleId = computed(() => route.params.id as string)

// Markdown 渲染器
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
})

// ============ 状态 ============

const loading = ref(true)
const article = ref<ArticleResponse | null>(null)
const error = ref<string | null>(null)

// 当前选中的图片
const selectedImage = ref<ImageInfo | null>(null)
const imagePreviewVisible = ref(false)

// 复制成功提示
const copySuccess = ref(false)

// ============ 方法 ============

// 获取文章详情
async function fetchArticle() {
  loading.value = true
  error.value = null

  try {
    const res = await getArticle(articleId.value)
    article.value = res.data
  } catch (err: any) {
    error.value = err.message || '获取文章失败'
    message.error(error.value)
  } finally {
    loading.value = false
  }
}

// 渲染 Markdown
function renderMarkdown(content: string): string {
  return md.render(content)
}

// 导出文章
async function handleExport() {
  if (!article.value) return

  try {
    const res = await exportArticle(article.value.id)
    const data = res.data

    if (data.format === 'html' && data.html) {
      // 导出 HTML 文件
      const fullHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${data.title}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; color: #333; }
    h1 { font-size: 28px; margin: 24px 0 16px; }
    h2 { font-size: 24px; margin: 20px 0 12px; }
    h3 { font-size: 20px; margin: 16px 0 8px; }
    img { max-width: 100%; height: auto; border-radius: 8px; margin: 16px 0; display: block; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    p { margin: 12px 0; }
    ul, ol { padding-left: 24px; }
    blockquote { border-left: 4px solid #ddd; padding-left: 16px; color: #666; margin: 16px 0; }
    code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }
    pre { background: #f5f5f5; padding: 16px; border-radius: 8px; overflow-x: auto; }
  </style>
</head>
<body>
  <h1>${data.title}</h1>
  ${data.html}
</body>
</html>`
      const blob = new Blob([fullHtml], { type: 'text/html' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${data.title}.html`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } else {
      // 导出 Markdown
      const blob = new Blob([`# ${data.title}\n\n${data.content}`], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${data.title}.md`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }

    message.success('文章已导出')
  } catch (err: any) {
    message.error(err.message || '导出失败')
  }
}

// 复制全文
async function handleCopy() {
  if (!article.value?.final_output && !article.value?.content) {
    message.warning('没有可复制的内容')
    return
  }

  const content = article.value.final_output || article.value.content || ''

  try {
    await navigator.clipboard.writeText(content)
    copySuccess.value = true
    message.success('已复制到剪贴板')
    setTimeout(() => {
      copySuccess.value = false
    }, 2000)
  } catch (err) {
    message.error('复制失败')
  }
}

// 删除文章
async function handleDelete() {
  if (!article.value) return

  // 显示确认框
  // 这里用 window.confirm 简化，实际项目应该用 Modal
  if (!confirm('确定要删除这篇文章吗？此操作不可恢复。')) {
    return
  }

  try {
    await deleteArticle(article.value.id)
    message.success('文章已删除')
    router.push({ name: 'history' })
  } catch (err: any) {
    message.error(err.message || '删除失败')
  }
}

// 分享文章
function handleShare() {
  if (navigator.share) {
    navigator.share({
      title: article.value?.selected_title || 'AI 生成的文章',
      text: `查看这篇由 AI 生成的文章：${article.value?.selected_title}`,
      url: window.location.href,
    }).catch(() => {})
  } else {
    // 复制链接
    navigator.clipboard.writeText(window.location.href)
    message.success('链接已复制')
  }
}

// 查看图片大图
function viewImage(img: ImageInfo) {
  selectedImage.value = img
  imagePreviewVisible.value = true
}

// 返回历史记录
function goBack() {
  router.push({ name: 'history' })
}

// ============ 生命周期 ============

onMounted(() => {
  fetchArticle()
})
</script>

<template>
  <div class="result-page">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <a-spin size="large" />
      <p>加载文章中...</p>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <a-result
        status="error"
        title="加载失败"
        :sub-title="error"
      >
        <template #extra>
          <a-space>
            <a-button type="primary" @click="fetchArticle">重新加载</a-button>
            <a-button @click="goBack">返回列表</a-button>
          </a-space>
        </template>
      </a-result>
    </div>

    <!-- 文章内容 -->
    <div v-else-if="article" class="article-container fade-in">
      <!-- 文章头部 -->
      <div class="article-header glass-card">
        <div class="header-top">
          <a-button type="text" @click="goBack">
            <template #icon><ArrowLeftOutlined /></template>
            返回
          </a-button>
          <div class="header-actions">
            <a-space>
              <a-button @click="handleCopy">
                <template #icon>
                  <CheckOutlined v-if="copySuccess" style="color: var(--cta-color)" />
                  <CopyOutlined v-else />
                </template>
                {{ copySuccess ? '已复制' : '复制全文' }}
              </a-button>
              <a-button type="primary" @click="handleExport">
                <template #icon><DownloadOutlined /></template>
                导出文章
              </a-button>
              <a-dropdown>
                <a-button>
                  更多操作
                </a-button>
                <template #overlay>
                  <a-menu>
                    <a-menu-item key="share" @click="handleShare">
                      <ShareAltOutlined /> 分享文章
                    </a-menu-item>
                    <a-menu-divider />
                    <a-menu-item key="delete" danger @click="handleDelete">
                      <DeleteOutlined /> 删除文章
                    </a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
            </a-space>
          </div>
        </div>

        <h1 class="article-title">{{ article.selected_title || '未命名文章' }}</h1>

        <div class="article-meta">
          <span class="meta-item">
            <FileTextOutlined />
            {{ article.word_count || 0 }} 字
          </span>
          <span class="meta-item">
            <PictureOutlined />
            {{ article.images?.length || 0 }} 张配图
          </span>
          <span class="meta-item">
            <EditOutlined />
            {{ new Date(article.updated_at).toLocaleDateString('zh-CN') }}
          </span>
        </div>
      </div>

      <!-- 内容区域 -->
      <div class="content-area">
        <!-- 文章正文 -->
        <div class="content-main">
          <a-card class="content-card" title="文章正文">
            <template #extra>
              <a-tag color="green">已完成</a-tag>
            </template>

            <div
              v-if="article.final_html"
              class="rich-content"
              v-html="article.final_html"
            />
            <div
              v-else-if="article.final_output || article.content"
              class="markdown-content"
              v-html="renderMarkdown(article.final_output || article.content || '')"
            />
            <a-empty v-else description="暂无内容" />
          </a-card>
        </div>

        <!-- 侧边栏 -->
        <div class="content-sidebar">
          <!-- 配图卡片 -->
          <a-card
            v-if="article.images && article.images.length"
            class="sidebar-card"
            :title="`配图 (${article.images.length})`"
          >
            <div class="image-grid">
              <div
                v-for="(img, index) in article.images"
                :key="index"
                class="image-item cursor-pointer"
                @click="viewImage(img)"
              >
                <img :src="img.url" :alt="img.position" />
                <div class="image-overlay">
                  <span class="image-source">{{ img.source }}</span>
                </div>
              </div>
            </div>
          </a-card>

          <!-- 大纲卡片 -->
          <a-card
            v-if="article.outline"
            class="sidebar-card"
            title="文章大纲"
          >
            <div class="outline-list">
              <div
                v-for="(section, index) in article.outline.sections"
                :key="index"
                class="outline-item"
              >
                <span class="outline-dot"></span>
                <span class="outline-text">{{ section.title }}</span>
              </div>
            </div>
          </a-card>

          <!-- 标题方案卡片 -->
          <a-card
            v-if="article.title_options && article.title_options.length"
            class="sidebar-card"
            title="备选标题"
          >
            <div class="title-list">
              <div
                v-for="opt in article.title_options"
                :key="opt.index"
                class="title-option"
                :class="{ selected: opt.title === article.selected_title }"
              >
                <CheckOutlined v-if="opt.title === article.selected_title" class="selected-icon" />
                <span>{{ opt.title }}</span>
              </div>
            </div>
          </a-card>
        </div>
      </div>
    </div>

    <!-- 图片预览弹窗 -->
    <a-modal
      v-model:open="imagePreviewVisible"
      :footer="null"
      :width="800"
      centered
      class="image-preview-modal"
    >
      <div v-if="selectedImage" class="preview-content">
        <img :src="selectedImage.url" :alt="selectedImage.position" />
        <div class="preview-info">
          <p><strong>位置:</strong> {{ selectedImage.position }}</p>
          <p><strong>来源:</strong> {{ selectedImage.source }}</p>
          <p v-if="selectedImage.keywords?.length">
            <strong>关键词:</strong> {{ selectedImage.keywords.join(', ') }}
          </p>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<style scoped>
.result-page {
  padding: 0;
}

/* 加载状态 */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.loading-state p {
  margin-top: 16px;
  color: var(--text-secondary);
}

/* 文章容器 */
.article-container {
  max-width: 1200px;
  margin: 0 auto;
}

/* 文章头部 */
.article-header {
  padding: 24px;
  margin-bottom: 24px;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.article-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 16px 0;
  line-height: 1.4;
}

.article-meta {
  display: flex;
  gap: 24px;
  color: var(--text-secondary);
  font-size: 14px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 内容区域 */
.content-area {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
}

/* 主内容 */
.content-main {
  min-width: 0;
}

.content-card {
  min-height: 500px;
}

/* 侧边栏 */
.content-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar-card {
  flex-shrink: 0;
}

/* 配图网格 */
.image-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.image-item {
  position: relative;
  aspect-ratio: 4/3;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f5f5;
}

.image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s ease;
}

.image-item:hover img {
  transform: scale(1.05);
}

.image-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 6px 8px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
}

.image-source {
  font-size: 11px;
  color: white;
}

/* 大纲列表 */
.outline-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.outline-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--text-secondary);
}

.outline-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary-color);
  flex-shrink: 0;
}

.outline-text {
  line-height: 1.4;
}

/* 标题列表 */
.title-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.title-option {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 6px;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.title-option.selected {
  background: rgba(34, 197, 94, 0.1);
  border-color: var(--cta-color);
  color: var(--text-primary);
}

.selected-icon {
  color: var(--cta-color);
  margin-right: 6px;
}

/* 图片预览 */
.preview-content {
  text-align: center;
}

.preview-content img {
  max-width: 100%;
  max-height: 70vh;
  border-radius: 8px;
}

.preview-info {
  margin-top: 16px;
  text-align: left;
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
}

.preview-info p {
  margin: 8px 0;
  font-size: 14px;
  color: var(--text-secondary);
}

/* HTML 富文本内容样式 */
.content-main :deep(.rich-content) {
  line-height: 1.8;
  color: var(--text-primary);
}

.content-main :deep(.rich-content h1),
.content-main :deep(.rich-content h2),
.content-main :deep(.rich-content h3),
.content-main :deep(.rich-content h4) {
  font-weight: 600;
  margin: 24px 0 16px 0;
  color: var(--text-primary);
}

.content-main :deep(.rich-content h1) { font-size: 28px; }
.content-main :deep(.rich-content h2) { font-size: 24px; }
.content-main :deep(.rich-content h3) { font-size: 20px; }

.content-main :deep(.rich-content p) {
  margin: 12px 0;
}

.content-main :deep(.rich-content img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-md);
  margin: 16px 0;
  box-shadow: var(--shadow-md);
  display: block;
}

.content-main :deep(.rich-content ul),
.content-main :deep(.rich-content ol) {
  padding-left: 24px;
  margin: 12px 0;
}

.content-main :deep(.rich-content blockquote) {
  border-left: 4px solid var(--primary-light);
  padding-left: 16px;
  color: var(--text-secondary);
  margin: 16px 0;
}

.content-main :deep(.rich-content pre) {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
}

.content-main :deep(.rich-content code) {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.9em;
}

/* Markdown 内容中的图片样式（关键：确保图片可见） */
.content-main :deep(.markdown-content img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-md);
  margin: 16px 0;
  box-shadow: var(--shadow-md);
  display: block;
}

/* 响应式 */
@media (max-width: 1024px) {
  .content-area {
    grid-template-columns: 1fr;
  }

  .content-sidebar {
    order: -1;
    flex-direction: row;
    flex-wrap: wrap;
  }

  .sidebar-card {
    flex: 1;
    min-width: 280px;
  }
}

@media (max-width: 768px) {
  .article-title {
    font-size: 22px;
  }

  .header-top {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions :deep(.ant-space) {
    width: 100%;
    justify-content: flex-end;
  }

  .article-meta {
    flex-wrap: wrap;
    gap: 12px;
  }
}
</style>