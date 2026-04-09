<script setup lang="ts">
/**
 * 关于页面
 * 展示产品介绍、技术架构、团队信息
 */
import { h } from 'vue'
import {
  InfoCircleOutlined,
  BulbOutlined,
  EditOutlined,
  FileTextOutlined,
  PictureOutlined,
  ApiOutlined,
  DatabaseOutlined,
  CloudOutlined,
  CodeOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  GithubOutlined,
} from '@ant-design/icons-vue'

// 技术栈
const techStack = [
  {
    category: '前端技术',
    items: [
      { name: 'Vue 3', desc: '渐进式 JavaScript 框架' },
      { name: 'TypeScript', desc: '类型安全的 JavaScript' },
      { name: 'Vite', desc: '下一代前端构建工具' },
      { name: 'Ant Design Vue', desc: '企业级 UI 组件库' },
      { name: 'Pinia', desc: 'Vue 状态管理' },
    ],
  },
  {
    category: '后端技术',
    items: [
      { name: 'FastAPI', desc: '现代 Python Web 框架' },
      { name: 'SQLAlchemy', desc: 'Python ORM 框架' },
      { name: 'Redis', desc: '高性能缓存数据库' },
      { name: 'SQLite', desc: '轻量级数据库' },
      { name: 'SSE', desc: '服务端实时推送' },
    ],
  },
  {
    category: 'AI 服务',
    items: [
      { name: '千问', desc: '阿里云大语言模型' },
      { name: '智谱 GLM', desc: '清华智谱 AI 模型' },
      { name: 'Pexels', desc: '高质量免费图库' },
      { name: 'Seedream', desc: '字节跳动 AI 绘图' },
      { name: '腾讯云 COS', desc: '对象存储服务' },
    ],
  },
]

// 智能体列表 - 使用渲染函数
const agents = [
  {
    name: 'TitleAgent',
    renderIcon: () => h(BulbOutlined),
    desc: '分析选题内容，生成多个爆款标题方案',
    color: '#0891B2',
  },
  {
    name: 'OutlineAgent',
    renderIcon: () => h(EditOutlined),
    desc: '根据选定标题，生成结构化文章大纲',
    color: '#22C55E',
  },
  {
    name: 'ContentAgent',
    renderIcon: () => h(FileTextOutlined),
    desc: '按大纲撰写文章正文，支持流式输出',
    color: '#F59E0B',
  },
  {
    name: 'ImageAnalyzerAgent',
    renderIcon: () => h(PictureOutlined),
    desc: '分析正文内容，确定配图需求和位置',
    color: '#EC4899',
  },
  {
    name: 'ImageGeneratorAgent',
    renderIcon: () => h(PictureOutlined),
    desc: '并行处理配图任务，多种来源智能选择',
    color: '#8B5CF6',
  },
]
</script>

<template>
  <div class="about-page">
    <!-- 页面头部 -->
    <section class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">
          <InfoCircleOutlined class="title-icon" />
          关于自媒体爆款文章生成器
        </h1>
        <p class="hero-subtitle">
          基于 AI 多智能体协作的文章创作系统<br />
          让写作变得简单高效
        </p>
      </div>
    </section>

    <!-- 产品介绍 -->
    <section class="intro-section">
      <div class="section-container">
        <div class="intro-content glass-card">
          <h2>产品愿景</h2>
          <p>
            自媒体时代，优质内容是获取流量的关键。然而，从选题到成稿往往需要耗费大量时间和精力。
            我们希望通过 AI 技术，将创作流程标准化、自动化，让每个人都能轻松产出高质量文章。
          </p>
          <p>
            本系统采用多智能体协作架构，将文章创作拆分为标题、大纲、正文、配图四个独立环节，
            每个环节由专门的智能体负责，协同完成高质量文章的创作。
          </p>
        </div>
      </div>
    </section>

    <!-- 智能体介绍 -->
    <section class="agents-section">
      <div class="section-container">
        <h2 class="section-title">五大智能体</h2>
        <p class="section-subtitle">分工明确，协作高效</p>

        <div class="agents-grid">
          <div
            v-for="(agent, index) in agents"
            :key="index"
            class="agent-card glass-card"
          >
            <div class="agent-icon" :style="{ background: agent.color }">
              <component :is="agent.renderIcon" />
            </div>
            <h3 class="agent-name">{{ agent.name }}</h3>
            <p class="agent-desc">{{ agent.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 核心特性 -->
    <section class="features-section">
      <div class="section-container">
        <h2 class="section-title">核心特性</h2>

        <div class="features-grid">
          <div class="feature-item">
            <ThunderboltOutlined class="feature-icon" />
            <div class="feature-content">
              <h3>实时流式输出</h3>
              <p>SSE 技术实现内容实时推送，创作过程可视化</p>
            </div>
          </div>
          <div class="feature-item">
            <ApiOutlined class="feature-icon" />
            <div class="feature-content">
              <h3>多模型支持</h3>
              <p>支持多种 AI 模型，可根据需求灵活切换</p>
            </div>
          </div>
          <div class="feature-item">
            <SafetyOutlined class="feature-icon" />
            <div class="feature-content">
              <h3>数据安全</h3>
              <p>本地存储，数据完全由用户掌控</p>
            </div>
          </div>
          <div class="feature-item">
            <CloudOutlined class="feature-icon" />
            <div class="feature-content">
              <h3>云端配图</h3>
              <p>自动上传云端 CDN，图片访问速度快</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 技术架构 -->
    <section class="tech-section">
      <div class="section-container">
        <h2 class="section-title">
          <CodeOutlined class="section-icon" />
          技术架构
        </h2>

        <div class="tech-grid">
          <div v-for="(tech, index) in techStack" :key="index" class="tech-category glass-card">
            <h3 class="category-title">{{ tech.category }}</h3>
            <div class="tech-list">
              <div v-for="(item, idx) in tech.items" :key="idx" class="tech-item">
                <span class="tech-name">{{ item.name }}</span>
                <span class="tech-desc">{{ item.desc }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 数据安全 -->
    <section class="security-section">
      <div class="section-container">
        <div class="security-content glass-card">
          <DatabaseOutlined class="security-icon" />
          <h2>数据安全承诺</h2>
          <ul>
            <li>所有文章数据存储在本地数据库，完全由您掌控</li>
            <li>API Key 等敏感信息仅存储在本地环境变量中</li>
            <li>配图文件存储于您的腾讯云 COS，不经过第三方服务器</li>
            <li>支持完全离线运行（使用本地模型时）</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- 开源信息 -->
    <section class="opensource-section">
      <div class="section-container">
        <div class="opensource-content">
          <h2>开源精神</h2>
          <p>本项目采用 MIT 开源协议，欢迎 Star、Fork 和贡献代码</p>
          <a-button type="primary" size="large">
            <template #icon><GithubOutlined /></template>
            查看源码
          </a-button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.about-page {
  padding: 0;
}

/* Hero 区域 */
.hero-section {
  padding: 60px 24px;
  background: linear-gradient(135deg, var(--bg-color) 0%, #F0F9FF 100%);
  text-align: center;
}

.hero-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 16px 0;
}

.title-icon {
  margin-right: 12px;
  color: var(--primary-color);
}

.hero-subtitle {
  font-size: 16px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.7;
}

/* 通用 */
.section-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 24px;
}

.section-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  text-align: center;
  margin: 0 0 8px 0;
}

.section-icon {
  margin-right: 8px;
  color: var(--primary-color);
}

.section-subtitle {
  font-size: 15px;
  color: var(--text-secondary);
  text-align: center;
  margin: 0 0 40px 0;
}

/* 产品介绍 */
.intro-section {
  padding: 60px 0;
  background: white;
}

.intro-content {
  padding: 40px;
}

.intro-content h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 20px 0;
}

.intro-content p {
  font-size: 15px;
  color: var(--text-secondary);
  line-height: 1.8;
  margin: 0 0 16px 0;
}

/* 智能体 */
.agents-section {
  padding: 60px 0;
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.agent-card {
  padding: 24px 16px;
  text-align: center;
}

.agent-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  border-radius: 14px;
  font-size: 24px;
  color: white;
}

.agent-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.agent-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

/* 核心特性 */
.features-section {
  padding: 60px 0;
  background: white;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  margin-top: 40px;
}

.feature-item {
  display: flex;
  gap: 16px;
  padding: 24px;
  background: var(--bg-color);
  border-radius: 12px;
}

.feature-icon {
  font-size: 28px;
  color: var(--primary-color);
  flex-shrink: 0;
}

.feature-content h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.feature-content p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
}

/* 技术架构 */
.tech-section {
  padding: 60px 0;
}

.tech-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-top: 40px;
}

.tech-category {
  padding: 24px;
}

.category-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--primary-light);
}

.tech-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tech-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tech-name {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 14px;
}

.tech-desc {
  font-size: 12px;
  color: var(--text-muted);
}

/* 数据安全 */
.security-section {
  padding: 60px 0;
  background: white;
}

.security-content {
  padding: 40px;
  text-align: center;
}

.security-icon {
  font-size: 48px;
  color: var(--primary-color);
  margin-bottom: 20px;
}

.security-content h2 {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 24px 0;
}

.security-content ul {
  list-style: none;
  padding: 0;
  margin: 0;
  text-align: left;
  max-width: 500px;
  margin: 0 auto;
}

.security-content li {
  padding: 10px 0;
  font-size: 15px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-light);
}

.security-content li:last-child {
  border-bottom: none;
}

.security-content li::before {
  content: '✓';
  color: var(--cta-color);
  font-weight: bold;
  margin-right: 12px;
}

/* 开源 */
.opensource-section {
  padding: 60px 0;
}

.opensource-content {
  text-align: center;
}

.opensource-content h2 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.opensource-content p {
  font-size: 15px;
  color: var(--text-secondary);
  margin: 0 0 24px 0;
}

/* 响应式 */
@media (max-width: 1024px) {
  .agents-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .tech-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 24px;
  }

  .section-title {
    font-size: 22px;
  }

  .agents-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .tech-grid {
    grid-template-columns: 1fr;
  }
}
</style>