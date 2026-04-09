<script setup lang="ts">
/**
 * 首页组件
 * 展示产品介绍、快速开始入口、功能特点
 */
import { ref, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  RocketOutlined,
  BulbOutlined,
  EditOutlined,
  PictureOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  StarOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()

// 表单状态
const topic = ref('')
const style = ref('专业')

// 风格选项
const styleOptions = [
  { value: '专业', label: '专业', desc: '严谨客观，适合行业分析' },
  { value: '轻松', label: '轻松', desc: '活泼有趣，适合生活分享' },
  { value: '幽默', label: '幽默', desc: '风趣诙谐，吸引眼球' },
  { value: '深度', label: '深度', desc: '深入剖析，引发思考' },
  { value: '热点', label: '热点', desc: '紧跟时事，快速传播' },
  { value: '教程', label: '教程', desc: '步骤清晰，实用性强' },
]

// 功能特点 - 使用渲染函数
const features = [
  {
    renderIcon: () => h(BulbOutlined),
    title: '智能标题',
    desc: 'AI 分析选题，生成多个爆款标题方案，助你选择最吸引眼球的标题',
    color: '#0891B2',
  },
  {
    renderIcon: () => h(EditOutlined),
    title: '结构大纲',
    desc: '自动生成结构化大纲，支持实时编辑和 AI 优化，让文章逻辑更清晰',
    color: '#22C55E',
  },
  {
    renderIcon: () => h(ThunderboltOutlined),
    title: '流式正文',
    desc: '正文内容实时流式输出，所见即所得，创作过程更加直观',
    color: '#F59E0B',
  },
  {
    renderIcon: () => h(PictureOutlined),
    title: '智能配图',
    desc: '多种配图服务并行处理，图库搜索、AI 绘图一应俱全',
    color: '#EC4899',
  },
]

// 开始创作
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
  <div class="home-page">
    <!-- Hero 区域 -->
    <section class="hero-section">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-badge fade-in">
          <StarOutlined />
          <span>AI 多智能体协作</span>
        </div>
        <h1 class="hero-title fade-in-up">
          自媒体爆款文章生成器
        </h1>
        <p class="hero-subtitle fade-in-up">
          输入选题想法，AI 自动完成标题、大纲、正文和配图<br />
          让创作效率提升 10 倍
        </p>

        <!-- 快速开始 -->
        <div class="quick-start glass-card fade-in-up">
          <a-form layout="vertical">
            <a-form-item label="你的选题想法">
              <a-textarea
                v-model:value="topic"
                placeholder="例如：如何在30天内打造爆款自媒体账号"
                :rows="3"
                :maxlength="500"
                show-count
              />
            </a-form-item>
            <a-form-item label="文章风格">
              <div class="style-options">
                <div
                  v-for="opt in styleOptions"
                  :key="opt.value"
                  class="style-option cursor-pointer"
                  :class="{ active: style === opt.value }"
                  @click="style = opt.value"
                >
                  <span class="style-label">{{ opt.label }}</span>
                  <span class="style-desc">{{ opt.desc }}</span>
                </div>
              </div>
            </a-form-item>
            <a-form-item>
              <a-button
                type="primary"
                size="large"
                block
                @click="handleStart"
                :disabled="!topic.trim()"
              >
                <template #icon><RocketOutlined /></template>
                开始创作
              </a-button>
            </a-form-item>
          </a-form>
        </div>
      </div>
    </section>

    <!-- 功能特点 -->
    <section class="features-section">
      <div class="section-container">
        <h2 class="section-title">四大核心功能</h2>
        <p class="section-subtitle">多智能体协作，从选题到成稿，全程 AI 辅助</p>

        <div class="features-grid">
          <div
            v-for="(feature, index) in features"
            :key="index"
            class="feature-card glass-card fade-in-up"
            :style="{ animationDelay: `${index * 100}ms` }"
          >
            <div class="feature-icon" :style="{ background: feature.color }">
              <component :is="feature.renderIcon" />
            </div>
            <h3 class="feature-title">{{ feature.title }}</h3>
            <p class="feature-desc">{{ feature.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 工作流程 -->
    <section class="workflow-section">
      <div class="section-container">
        <h2 class="section-title">创作流程</h2>
        <p class="section-subtitle">简单四步，完成爆款文章</p>

        <div class="workflow-steps">
          <div class="workflow-step">
            <div class="step-number">01</div>
            <div class="step-content">
              <h3>输入选题</h3>
              <p>描述你的创作想法和期望风格</p>
            </div>
          </div>
          <div class="workflow-arrow">
            <CheckCircleOutlined />
          </div>
          <div class="workflow-step">
            <div class="step-number">02</div>
            <div class="step-content">
              <h3>选择标题</h3>
              <p>AI 生成多个标题方案供你选择</p>
            </div>
          </div>
          <div class="workflow-arrow">
            <CheckCircleOutlined />
          </div>
          <div class="workflow-step">
            <div class="step-number">03</div>
            <div class="step-content">
              <h3>确认大纲</h3>
              <p>编辑调整文章结构大纲</p>
            </div>
          </div>
          <div class="workflow-arrow">
            <CheckCircleOutlined />
          </div>
          <div class="workflow-step">
            <div class="step-number">04</div>
            <div class="step-content">
              <h3>生成正文</h3>
              <p>流式输出正文并自动配图</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 优势 -->
    <section class="advantages-section">
      <div class="section-container">
        <div class="advantages-content glass-card">
          <h2 class="section-title">为什么选择我们</h2>
          <div class="advantages-list">
            <div class="advantage-item">
              <SafetyOutlined class="advantage-icon" />
              <span>数据安全，本地存储</span>
            </div>
            <div class="advantage-item">
              <ApiOutlined class="advantage-icon" />
              <span>多模型支持，按需切换</span>
            </div>
            <div class="advantage-item">
              <ThunderboltOutlined class="advantage-icon" />
              <span>SSE 实时推送，体验流畅</span>
            </div>
            <div class="advantage-item">
              <StarOutlined class="advantage-icon" />
              <span>专业优化，爆款思维</span>
            </div>
          </div>
          <a-button type="primary" size="large" @click="router.push({ name: 'create' })">
            立即体验
          </a-button>
        </div>
      </div>
    </section>

    <!-- 底部 CTA -->
    <section class="cta-section">
      <div class="cta-content">
        <h2>准备好创作爆款文章了吗？</h2>
        <p>只需一个想法，剩下的交给 AI</p>
        <a-button type="primary" size="large" @click="router.push({ name: 'create' })">
          <template #icon><RocketOutlined /></template>
          开始创作
        </a-button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-page {
  min-height: 100vh;
}

/* Hero 区域 */
.hero-section {
  position: relative;
  padding: 80px 24px 120px;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, var(--bg-color) 0%, #F0F9FF 50%, #E0F2FE 100%);
  z-index: -1;
}

.hero-bg::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(8, 145, 178, 0.15) 0%, transparent 70%);
  border-radius: 50%;
}

.hero-content {
  max-width: 800px;
  margin: 0 auto;
  text-align: center;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(8, 145, 178, 0.1);
  border-radius: 20px;
  font-size: 14px;
  color: var(--primary-color);
  margin-bottom: 24px;
}

.hero-title {
  font-size: 42px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 16px 0;
  line-height: 1.3;
}

.hero-subtitle {
  font-size: 18px;
  color: var(--text-secondary);
  margin: 0 0 40px 0;
  line-height: 1.7;
}

/* 快速开始 */
.quick-start {
  max-width: 500px;
  margin: 0 auto;
  padding: 32px;
  text-align: left;
}

.style-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.style-option {
  padding: 12px;
  border: 2px solid var(--border-light);
  border-radius: 12px;
  text-align: center;
  transition: all 0.2s ease;
}

.style-option:hover {
  border-color: var(--primary-light);
  background: rgba(8, 145, 178, 0.02);
}

.style-option.active {
  border-color: var(--primary-color);
  background: rgba(8, 145, 178, 0.05);
}

.style-label {
  display: block;
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.style-desc {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
}

/* 功能特点 */
.features-section {
  padding: 80px 24px;
  background: white;
}

.section-container {
  max-width: 1200px;
  margin: 0 auto;
}

.section-title {
  font-size: 32px;
  font-weight: 700;
  text-align: center;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.section-subtitle {
  font-size: 16px;
  text-align: center;
  color: var(--text-secondary);
  margin: 0 0 48px 0;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.feature-card {
  padding: 32px 24px;
  text-align: center;
  transition: all 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-4px);
}

.feature-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  border-radius: 16px;
  font-size: 28px;
  color: white;
}

.feature-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.feature-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
}

/* 工作流程 */
.workflow-section {
  padding: 80px 24px;
  background: linear-gradient(180deg, #F8FAFC 0%, white 100%);
}

.workflow-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.workflow-step {
  flex: 1;
  min-width: 200px;
  max-width: 240px;
  padding: 24px;
  background: white;
  border-radius: 16px;
  box-shadow: var(--shadow-sm);
  text-align: center;
}

.step-number {
  font-size: 28px;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: 12px;
}

.step-content h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.step-content p {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}

.workflow-arrow {
  font-size: 24px;
  color: var(--cta-color);
}

/* 优势 */
.advantages-section {
  padding: 80px 24px;
}

.advantages-content {
  max-width: 600px;
  margin: 0 auto;
  padding: 48px;
  text-align: center;
}

.advantages-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  margin-bottom: 32px;
}

.advantage-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  color: var(--text-secondary);
  text-align: left;
}

.advantage-icon {
  font-size: 20px;
  color: var(--primary-color);
}

/* CTA */
.cta-section {
  padding: 100px 24px;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%);
  text-align: center;
}

.cta-content h2 {
  font-size: 32px;
  font-weight: 700;
  color: white;
  margin: 0 0 12px 0;
}

.cta-content p {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.9);
  margin: 0 0 32px 0;
}

.cta-content :deep(.ant-btn-primary) {
  background: white !important;
  color: var(--primary-color) !important;
  border: none !important;
}

.cta-content :deep(.ant-btn-primary:hover) {
  background: #F0F9FF !important;
}

/* 响应式 */
@media (max-width: 1024px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .hero-section {
    padding: 48px 16px 80px;
  }

  .hero-title {
    font-size: 28px;
  }

  .hero-subtitle {
    font-size: 15px;
  }

  .quick-start {
    padding: 20px;
  }

  .style-options {
    grid-template-columns: repeat(2, 1fr);
  }

  .features-section,
  .workflow-section,
  .advantages-section {
    padding: 48px 16px;
  }

  .features-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .section-title {
    font-size: 24px;
  }

  .workflow-steps {
    flex-direction: column;
  }

  .workflow-arrow {
    transform: rotate(90deg);
  }

  .advantages-list {
    grid-template-columns: 1fr;
  }

  .cta-section {
    padding: 60px 16px;
  }

  .cta-content h2 {
    font-size: 24px;
  }
}
</style>