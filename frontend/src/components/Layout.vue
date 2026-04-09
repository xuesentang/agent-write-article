<script setup lang="ts">
/**
 * 全局布局组件
 * 采用 Glassmorphism 设计风格
 */
import { ref, watch, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  HomeOutlined,
  EditOutlined,
  HistoryOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()

// 当前选中的菜单 keys
const selectedKeys = ref<string[]>([])

// 监听路由变化更新选中状态
watch(
  () => route.name,
  (name) => {
    selectedKeys.value = [name as string]
  },
  { immediate: true }
)

// 菜单项 - 使用 h 函数渲染图标
const menuItems = [
  { key: 'home', label: '首页', icon: () => h(HomeOutlined) },
  { key: 'create', label: '创作文章', icon: () => h(EditOutlined) },
  { key: 'history', label: '历史记录', icon: () => h(HistoryOutlined) },
  { key: 'about', label: '关于', icon: () => h(InfoCircleOutlined) },
]

// 菜单点击
const handleMenuClick = ({ key }: { key: string }) => {
  router.push({ name: key })
}

// Logo 点击
const handleLogoClick = () => {
  router.push({ name: 'home' })
}
</script>

<template>
  <a-layout class="layout-container">
    <!-- 顶部导航栏 -->
    <a-layout-header class="header">
      <div class="header-inner">
        <!-- Logo -->
        <div class="logo cursor-pointer" @click="handleLogoClick">
          <ThunderboltOutlined class="logo-icon" />
          <span class="logo-text">自媒体爆款文章生成器</span>
        </div>

        <!-- 导航菜单 -->
        <a-menu
          v-model:selectedKeys="selectedKeys"
          mode="horizontal"
          class="nav-menu"
          :items="menuItems"
          @click="handleMenuClick"
        />

        <!-- 右侧操作区 -->
        <div class="header-actions">
          <a-button type="primary" @click="router.push({ name: 'create' })">
            <template #icon><EditOutlined /></template>
            开始创作
          </a-button>
        </div>
      </div>
    </a-layout-header>

    <!-- 主内容区 -->
    <a-layout-content class="main-content">
      <div class="content-wrapper">
        <slot />
      </div>
    </a-layout-content>

    <!-- 底部 -->
    <a-layout-footer class="footer">
      <div class="footer-inner">
        <p class="footer-title">自媒体爆款文章生成器</p>
        <p class="footer-desc">
          由 AI 多智能体协作驱动 · 千问大模型提供理解能力
        </p>
        <div class="footer-links">
          <a href="https://pexels.com" target="_blank" rel="noopener">Pexels 图库</a>
          <span class="divider">·</span>
          <a href="https://iconify.design" target="_blank" rel="noopener">Iconify 图标</a>
          <span class="divider">·</span>
          <a href="https://open.bigmodel.cn" target="_blank" rel="noopener">智谱 AI</a>
        </div>
        <p class="footer-copyright">© 2024 Powered by AI</p>
      </div>
    </a-layout-footer>
  </a-layout>
</template>

<style scoped>
.layout-container {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-color) 0%, #F0F9FF 50%, #E0F2FE 100%);
}

/* 头部导航 */
.header {
  position: sticky;
  top: 16px;
  left: 16px;
  right: 16px;
  z-index: 100;
  background: rgba(255, 255, 255, 0.8) !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
  padding: 0 24px;
  height: 64px;
  margin: 16px;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  max-width: 1400px;
  margin: 0 auto;
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 26px;
  color: var(--primary-color);
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 导航菜单 */
.nav-menu {
  flex: 1;
  display: flex;
  justify-content: center;
  background: transparent !important;
  border-bottom: none !important;
}

.nav-menu :deep(.ant-menu-item) {
  font-weight: 500;
  border-radius: 8px !important;
}

.nav-menu :deep(.ant-menu-item-selected) {
  background: rgba(8, 145, 178, 0.1) !important;
}

.nav-menu :deep(.ant-menu-item-selected::after) {
  border-bottom-color: var(--primary-color) !important;
}

/* 右侧操作 */
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 主内容 */
.main-content {
  background: transparent;
  padding: 24px;
  min-height: calc(100vh - 200px);
}

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
}

/* 底部 */
.footer {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid rgba(255, 255, 255, 0.3);
  padding: 40px 24px;
  text-align: center;
}

.footer-inner {
  max-width: 600px;
  margin: 0 auto;
}

.footer-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.footer-desc {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 16px;
}

.footer-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
}

.footer-links a {
  color: var(--text-secondary);
  font-size: 13px;
  transition: color 0.2s;
}

.footer-links a:hover {
  color: var(--primary-color);
}

.footer-links .divider {
  color: var(--text-muted);
}

.footer-copyright {
  font-size: 13px;
  color: var(--text-muted);
}

/* 响应式 */
@media (max-width: 768px) {
  .header {
    left: 8px;
    right: 8px;
    margin: 8px;
    padding: 0 12px;
  }

  .logo-text {
    display: none;
  }

  .header-actions {
    display: none;
  }

  .main-content {
    padding: 16px;
  }
}
</style>