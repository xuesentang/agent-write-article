<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
const articleId = route.params.id

// TODO: 从后端获取文章内容并展示
</script>

<template>
  <div class="result-container">
    <a-page-header
      title="文章详情"
      :sub-title="`ID: ${articleId}`"
      @back="$router.push('/history')"
    />

    <div class="article-section">
      <a-card title="文章内容" class="article-card">
        <div class="placeholder">
          <p>文章详情页面 - 待实现</p>
          <p>文章 ID: {{ articleId }}</p>
        </div>
      </a-card>

      <div class="actions-section">
        <a-space>
          <a-button type="primary">导出 Markdown</a-button>
          <a-button>复制全文</a-button>
          <a-button danger>删除文章</a-button>
        </a-space>
      </div>
    </div>
  </div>
</template>

<style scoped>
.result-container {
  padding: 24px;
}

.article-section {
  max-width: 800px;
  margin: 24px auto 0;
}

.article-card {
  margin-bottom: 24px;
}

.placeholder {
  text-align: center;
  padding: 48px;
  color: #666;
}

.actions-section {
  text-align: center;
}
</style>