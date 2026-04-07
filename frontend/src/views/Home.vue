<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { EditOutlined, RocketOutlined, BulbOutlined, PictureOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const topic = ref('')
const style = ref('专业')
const styles = ['专业', '轻松', '幽默', '深度', '热点', '教程']

const handleStart = () => {
  if (!topic.value.trim()) {
    return
  }
  router.push({
    name: 'create',
    query: { topic: topic.value, style: style.value },
  })
}
</script>

<template>
  <div class="home-container">
    <div class="hero-section">
      <h1 class="hero-title">
        <RocketOutlined class="hero-icon" />
        AI 驱动的爆款文章生成器
      </h1>
      <p class="hero-desc">
        输入您的选题想法，AI 将协助您完成标题、大纲、正文和配图，快速生成高质量文章
      </p>
    </div>

    <div class="input-section">
      <a-card title="开始创作" class="input-card">
        <a-form layout="vertical">
          <a-form-item label="选题描述">
            <a-textarea
              v-model:value="topic"
              placeholder="请输入您的选题想法，例如：如何在30天内打造爆款自媒体账号"
              :rows="4"
              :maxlength="500"
              show-count
            />
          </a-form-item>
          <a-form-item label="文章风格">
            <a-select v-model:value="style" :options="styles.map(s => ({ value: s, label: s }))" />
          </a-form-item>
          <a-form-item>
            <a-button type="primary" size="large" block @click="handleStart" :disabled="!topic.trim()">
              开始创作
            </a-button>
          </a-form-item>
        </a-form>
      </a-card>
    </div>

    <div class="features-section">
      <h2 class="features-title">核心功能</h2>
      <div class="features-grid">
        <a-card class="feature-card">
          <template #title>
            <BulbOutlined /> 智能标题
          </template>
          <p>AI 分析选题生成多个爆款标题方案，供您选择最合适的一个</p>
        </a-card>
        <a-card class="feature-card">
          <template #title>
            <EditOutlined /> 结构大纲
          </template>
          <p>根据标题自动生成结构化大纲，支持实时编辑和 AI 优化调整</p>
        </a-card>
        <a-card class="feature-card">
          <template #title>
            <EditOutlined /> 流式正文
          </template>
          <p>正文内容实时流式输出，您可以随时查看生成进度</p>
        </a-card>
        <a-card class="feature-card">
          <template #title>
            <PictureOutlined /> 智能配图
          </template>
          <p>多种配图服务并行处理，图库搜索、AI 绘图、图表生成一应俱全</p>
        </a-card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-container {
  padding: 24px;
}

.hero-section {
  text-align: center;
  margin-bottom: 48px;
}

.hero-title {
  font-size: 32px;
  font-weight: 700;
  color: #1890ff;
  margin-bottom: 16px;
}

.hero-icon {
  margin-right: 12px;
}

.hero-desc {
  font-size: 16px;
  color: #666;
  max-width: 600px;
  margin: 0 auto;
}

.input-section {
  max-width: 600px;
  margin: 0 auto 48px;
}

.input-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.features-section {
  max-width: 1200px;
  margin: 0 auto;
}

.features-title {
  font-size: 24px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 24px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.feature-card {
  text-align: center;
}

.feature-card p {
  color: #666;
  font-size: 14px;
}

@media (max-width: 1024px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .features-grid {
    grid-template-columns: 1fr;
  }
}
</style>