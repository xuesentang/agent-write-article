<script setup lang="ts">
</script>

<template>
  <div class="about-container">
    <a-page-header title="关于我们" />

    <div class="content-section">
      <a-card title="自媒体爆款文章生成器">
        <p>这是一个基于 AI 多智能体协作的文章生成系统。</p>
        <p>五大智能体分工协作：</p>
        <ul>
          <li><strong>TitleAgent</strong>：生成爆款标题方案</li>
          <li><strong>OutlineAgent</strong>：生成结构化大纲</li>
          <li><strong>ContentAgent</strong>：撰写文章正文</li>
          <li><strong>ImageAnalyzerAgent</strong>：分析配图需求</li>
          <li><strong>ImageGeneratorAgent</strong>：生成文章配图</li>
        </ul>
        <p>技术特点：</p>
        <ul>
          <li>SSE 流式实时推送</li>
          <li>图文并行处理</li>
          <li>用户可中途调整</li>
        </ul>
      </a-card>

      <a-card title="技术栈" class="tech-card">
        <p><strong>前端</strong>: Vue 3 + Vite + Ant Design Vue</p>
        <p><strong>后端</strong>: FastAPI + SQLAlchemy + Redis</p>
        <p><strong>AI 模型</strong>: DeepSeek / 智谱 GLM / 千问</p>
        <p><strong>配图服务</strong>: Pexels / Seedream / Mermaid / Iconify</p>
      </a-card>
    </div>
  </div>
</template>

<style scoped>
.about-container {
  padding: 24px;
}

.content-section {
  max-width: 800px;
  margin: 24px auto 0;
}

.tech-card {
  margin-top: 24px;
}

ul {
  padding-left: 24px;
  margin: 16px 0;
}

li {
  margin: 8px 0;
}
</style>