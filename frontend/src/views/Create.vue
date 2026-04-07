<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const topic = ref(route.query.topic || '')
const style = ref(route.query.style || '专业')

// TODO: 实现完整的创作流程
// 阶段 1: 标题生成
// 阶段 2: 大纲生成
// 阶段 3: 正文 + 配图
</script>

<template>
  <div class="create-container">
    <a-page-header
      title="创作文章"
      :sub-title="`选题: ${topic}`"
      @back="$router.push('/')"
    />

    <div class="workflow-section">
      <!-- 进度指示 -->
      <a-steps :current="0" class="progress-steps">
        <a-step title="标题生成" description="AI 生成多个标题方案" />
        <a-step title="大纲生成" description="根据标题生成结构化大纲" />
        <a-step title="正文创作" description="流式输出文章正文" />
        <a-step title="配图生成" description="并行生成文章配图" />
      </a-steps>

      <!-- 当前阶段内容 -->
      <a-card class="stage-card">
        <div class="stage-placeholder">
          <a-spin size="large" />
          <p>创作流程页面 - 待实现</p>
          <p>选题: {{ topic }}</p>
          <p>风格: {{ style }}</p>
        </div>
      </a-card>
    </div>
  </div>
</template>

<style scoped>
.create-container {
  padding: 24px;
}

.workflow-section {
  max-width: 800px;
  margin: 24px auto 0;
}

.progress-steps {
  margin-bottom: 24px;
}

.stage-card {
  min-height: 400px;
}

.stage-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #666;
}

.stage-placeholder p {
  margin: 12px 0;
}
</style>