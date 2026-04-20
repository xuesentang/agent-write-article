"""
错误码枚举定义
统一管理所有业务错误码，便于前后端对接和问题排查
"""

from enum import Enum


class ErrorCode(str, Enum):
    """错误码枚举"""

    # 通用错误 (1000-1099)
    SUCCESS = "1000"  # 成功（无错误）
    UNKNOWN_ERROR = "1001"  # 未知错误
    INVALID_REQUEST = "1002"  # 请求参数无效
    NOT_FOUND = "1003"  # 资源不存在
    PERMISSION_DENIED = "1004"  # 权限不足
    RATE_LIMITED = "1005"  # 请求频率限制

    # 用户相关错误 (1100-1199)
    USER_NOT_FOUND = "1100"  # 用户不存在
    USER_ALREADY_EXISTS = "1101"  # 用户已存在
    INVALID_PASSWORD = "1102"  # 密码错误
    TOKEN_EXPIRED = "1103"  # Token 过期
    TOKEN_INVALID = "1104"  # Token 无效

    # 任务相关错误 (1200-1299)
    TASK_NOT_FOUND = "1200"  # 任务不存在
    TASK_ALREADY_COMPLETED = "1201"  # 任务已完成
    TASK_ALREADY_FAILED = "1202"  # 任务已失败
    INVALID_TASK_STATUS = "1203"  # 任务状态无效
    TASK_CREATION_FAILED = "1204"  # 任务创建失败

    # 文章相关错误 (1300-1399)
    ARTICLE_NOT_FOUND = "1300"  # 文章不存在
    TITLE_GENERATION_FAILED = "1301"  # 标题生成失败
    OUTLINE_GENERATION_FAILED = "1302"  # 大纲生成失败
    CONTENT_GENERATION_FAILED = "1303"  # 正文生成失败

    # 配图相关错误 (1400-1499)
    IMAGE_GENERATION_FAILED = "1400"  # 图片生成失败
    IMAGE_UPLOAD_FAILED = "1401"  # 图片上传失败
    IMAGE_NOT_FOUND = "1402"  # 图片不存在
    IMAGE_PROVIDER_ERROR = "1403"  # 配图服务错误

    # LLM 相关错误 (1500-1599)
    LLM_API_ERROR = "1500"  # LLM API 调用失败
    LLM_TIMEOUT = "1501"  # LLM 调用超时
    LLM_RATE_LIMITED = "1502"  # LLM API 频率限制
    LLM_INVALID_RESPONSE = "1503"  # LLM 返回格式无效
    LLM_NO_API_KEY = "1504"  # LLM API Key 未配置

    # SSE 相关错误 (1600-1699)
    SSE_CONNECTION_ERROR = "1600"  # SSE 连接错误
    SSE_CONNECTION_TIMEOUT = "1601"  # SSE 连接超时
    SSE_STREAM_ERROR = "1602"  # SSE 流传输错误

    # 数据库相关错误 (1700-1799)
    DATABASE_ERROR = "1700"  # 数据库操作错误
    DATABASE_CONNECTION_ERROR = "1701"  # 数据库连接错误

    # Redis 相关错误 (1800-1899)
    REDIS_ERROR = "1800"  # Redis 操作错误
    REDIS_CONNECTION_ERROR = "1801"  # Redis 连接错误


class ErrorMessages:
    """错误消息映射"""

    _messages = {
        ErrorCode.SUCCESS: "操作成功",
        ErrorCode.UNKNOWN_ERROR: "系统发生未知错误",
        ErrorCode.INVALID_REQUEST: "请求参数无效",
        ErrorCode.NOT_FOUND: "请求的资源不存在",
        ErrorCode.PERMISSION_DENIED: "权限不足",
        ErrorCode.RATE_LIMITED: "请求频率超过限制",

        ErrorCode.USER_NOT_FOUND: "用户不存在",
        ErrorCode.USER_ALREADY_EXISTS: "用户已存在",
        ErrorCode.INVALID_PASSWORD: "密码错误",
        ErrorCode.TOKEN_EXPIRED: "登录已过期，请重新登录",
        ErrorCode.TOKEN_INVALID: "无效的身份凭证",

        ErrorCode.TASK_NOT_FOUND: "任务不存在",
        ErrorCode.TASK_ALREADY_COMPLETED: "任务已完成，无法修改",
        ErrorCode.TASK_ALREADY_FAILED: "任务已失败",
        ErrorCode.INVALID_TASK_STATUS: "任务状态无效",
        ErrorCode.TASK_CREATION_FAILED: "任务创建失败",

        ErrorCode.ARTICLE_NOT_FOUND: "文章不存在",
        ErrorCode.TITLE_GENERATION_FAILED: "标题生成失败",
        ErrorCode.OUTLINE_GENERATION_FAILED: "大纲生成失败",
        ErrorCode.CONTENT_GENERATION_FAILED: "正文生成失败",

        ErrorCode.IMAGE_GENERATION_FAILED: "图片生成失败",
        ErrorCode.IMAGE_UPLOAD_FAILED: "图片上传失败",
        ErrorCode.IMAGE_NOT_FOUND: "图片不存在",
        ErrorCode.IMAGE_PROVIDER_ERROR: "配图服务暂时不可用",

        ErrorCode.LLM_API_ERROR: "AI 模型调用失败",
        ErrorCode.LLM_TIMEOUT: "AI 模型响应超时",
        ErrorCode.LLM_RATE_LIMITED: "AI 模型调用频率受限，请稍后再试",
        ErrorCode.LLM_INVALID_RESPONSE: "AI 模型返回内容格式异常",
        ErrorCode.LLM_NO_API_KEY: "AI 服务 API Key 未配置",

        ErrorCode.SSE_CONNECTION_ERROR: "实时连接异常",
        ErrorCode.SSE_CONNECTION_TIMEOUT: "实时连接超时",
        ErrorCode.SSE_STREAM_ERROR: "数据流传输异常",

        ErrorCode.DATABASE_ERROR: "数据库操作失败",
        ErrorCode.DATABASE_CONNECTION_ERROR: "数据库连接失败",

        ErrorCode.REDIS_ERROR: "缓存服务异常",
        ErrorCode.REDIS_CONNECTION_ERROR: "缓存服务连接失败",
    }

    @classmethod
    def get_message(cls, code: ErrorCode) -> str:
        """获取错误码对应的默认消息"""
        return cls._messages.get(code, "未知错误")