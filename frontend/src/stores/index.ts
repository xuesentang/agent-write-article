/**
 * stores 模块初始化
 */

export { useTaskStore } from './task'
export type { TaskState } from './task'

// 从 API 重新导出类型
export type { TaskStatus } from '@/api'

// TODO: 添加其他 store
// export { useUserStore } from './user'
// export { useArticleStore } from './article'