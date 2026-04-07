<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { MenuOutlined, HomeOutlined, EditOutlined, HistoryOutlined, InfoCircleOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const currentRoute = ref(router.currentRoute.value.name)

router.afterEach((to) => {
  currentRoute.value = to.name
})

const menuItems = [
  { key: 'home', label: '首页', icon: HomeOutlined },
  { key: 'create', label: '创作文章', icon: EditOutlined },
  { key: 'history', label: '历史记录', icon: HistoryOutlined },
  { key: 'about', label: '关于', icon: InfoCircleOutlined },
]

const handleMenuClick = ({ key }: { key: string }) => {
  router.push({ name: key })
}
</script>

<template>
  <a-layout class="layout-container">
    <!-- 顶部导航栏 -->
    <a-layout-header class="header">
      <div class="header-content">
        <div class="logo" @click="router.push('/')">
          <span class="logo-icon">📝</span>
          <span class="logo-text">自媒体爆款文章生成器</span>
        </div>
        <a-menu
          v-model:selectedKeys="[currentRoute]"
          mode="horizontal"
          :items="menuItems"
          @click="handleMenuClick"
          class="nav-menu"
        />
      </div>
    </a-layout-header>

    <!-- 内容区域 -->
    <a-layout-content class="content">
      <div class="content-wrapper">
        <slot />
      </div>
    </a-layout-content>

    <!-- 底部版权信息 -->
    <a-layout-footer class="footer">
      <div class="footer-content">
        <p>自媒体爆款文章生成器 © 2024 Powered by AI</p>
        <p>使用 DeepSeek / 智谱 / 千问 等 AI 模型驱动</p>
      </div>
    </a-layout-footer>
  </a-layout>
</template>

<style scoped>
.layout-container {
  min-height: 100vh;
}

.header {
  background: #fff;
  padding: 0;
  height: 64px;
  border-bottom: 1px solid #f0f0f0;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  padding: 0 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.logo {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.logo-icon {
  font-size: 24px;
  margin-right: 8px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #1890ff;
}

.nav-menu {
  line-height: 62px;
  border-bottom: none;
}

.content {
  background: #f5f5f5;
  padding: 24px;
}

.content-wrapper {
  max-width: 1400px;
  margin: 0 auto;
}

.footer {
  background: #fff;
  padding: 24px 50px;
  text-align: center;
  border-top: 1px solid #f0f0f0;
}

.footer-content p {
  margin: 4px 0;
  color: #666;
  font-size: 14px;
}
</style>