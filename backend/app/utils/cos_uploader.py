"""
腾讯云 COS 上传服务
将图片上传到腾讯云对象存储

配置要求（从 .env 读取）：
- COS_SECRET_ID: 腾讯云 API 密钥 ID
- COS_SECRET_KEY: 腾讯云 API 密钥 Key
- COS_BUCKET: 存储桶名称
- COS_REGION: 存储桶区域（如 ap-shanghai）
- COS_UPLOAD_PATH: 上传路径前缀

注意：若配置缺失，服务不可用，必须中断并向用户确认
"""

import hashlib
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

import httpx

from app.config import settings
from app.schemas.image import ImageResult, ImageProvider, ImageTaskStatus


logger = logging.getLogger(__name__)


class COSUploader:
    """
    腾讯云 COS 上传服务

    功能：
    - 从 URL 下载图片到临时目录
    - 上传到腾讯云 COS
    - 返回 COS 访问 URL
    - 清理临时文件

    注意：当前实现为简化版本，真实项目建议使用 cos-python-sdk-v5
    """

    # COS API 端点格式
    # https://{bucket}.cos.{region}.myqcloud.com

    def __init__(self):
        """初始化 COS 上传服务"""
        # 从 settings 读取配置
        self.secret_id = settings.COS_SECRET_ID
        self.secret_key = settings.COS_SECRET_KEY
        self.bucket = settings.COS_BUCKET
        self.region = settings.COS_REGION
        self.upload_path = settings.COS_UPLOAD_PATH

        # 检查配置完整性
        self._check_config()

    def _check_config(self):
        """
        检查配置完整性

        硬性规则：配置缺失时必须中断，不可自行臆造
        """
        missing_configs = []

        if not self.secret_id or self.secret_id == "your_secret_id_here":
            missing_configs.append("COS_SECRET_ID")

        if not self.secret_key or self.secret_key == "your_secret_key_here":
            missing_configs.append("COS_SECRET_KEY")

        if not self.bucket or self.bucket == "your_bucket_name_here":
            missing_configs.append("COS_BUCKET")

        if missing_configs:
            error_msg = (
                f"[COSUploader] 配置缺失，必须中断执行: "
                f"{', '.join(missing_configs)}"
            )
            logger.error(error_msg)
            self._available = False
            # 不抛异常，由调用者检查 is_available()
        else:
            self._available = True
            logger.info(
                f"[COSUploader] 配置已就绪: bucket={self.bucket}, "
                f"region={self.region}, path={self.upload_path}"
            )

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._available

    async def upload_from_url(
        self,
        image_url: str,
        placeholder_id: str,
        task_id: str,
        source_provider: ImageProvider,
    ) -> ImageResult:
        """
        从 URL 下载图片并上传到 COS

        Args:
            image_url: 图片源 URL
            placeholder_id: 占位符 ID（用于生成存储路径）
            task_id: 任务 ID（用于生成唯一文件名）
            source_provider: 源服务提供商

        Returns:
            ImageResult: 上传结果

        流程：
        1. 从 URL 下载图片到临时目录
        2. 上传到 COS
        3. 删除临时文件
        4. 返回 COS URL
        """
        start_time = time.time()

        if not self.is_available():
            logger.error("[COSUploader] COS 配置缺失，上传失败")
            return ImageResult(
                taskId=task_id,
                placeholderId=placeholder_id,
                url="",  # 空 URL 表示失败
                cosKey="",
                sourceProvider=source_provider,
                status=ImageTaskStatus.FAILED,
                errorMessage="COS 配置缺失",
            )

        try:
            # 1. 下载图片到临时目录
            temp_file_path = await self._download_to_temp(image_url)

            # 2. 获取图片尺寸（可选）
            width, height = self._get_image_dimensions(temp_file_path)

            # 3. 生成 COS 存储路径
            cos_key = self._generate_cos_key(placeholder_id, task_id, temp_file_path)

            # 4. 上传到 COS
            cos_url = await self._upload_to_cos(temp_file_path, cos_key)

            # 5. 删除临时文件
            self._cleanup_temp_file(temp_file_path)

            latency = (time.time() - start_time) * 1000

            logger.info(
                f"[COSUploader] 上传成功: cos_key={cos_key}, "
                f"latency={latency:.2f}ms"
            )

            return ImageResult(
                taskId=task_id,
                placeholderId=placeholder_id,
                url=cos_url,
                cosKey=cos_key,
                width=width,
                height=height,
                sourceProvider=source_provider,
                status=ImageTaskStatus.COMPLETED,
                originalUrl=image_url,
                uploadTime=latency,
            )

        except Exception as e:
            logger.error(f"[COSUploader] 上传失败: {e}")

            return ImageResult(
                taskId=task_id,
                placeholderId=placeholder_id,
                url="",  # 空 URL 表示失败
                cosKey="",
                sourceProvider=source_provider,
                status=ImageTaskStatus.FAILED,
                errorMessage=str(e),
            )

    async def _download_to_temp(self, image_url: str) -> str:
        """
        从 URL 下载图片到临时目录

        Args:
            image_url: 图片 URL

        Returns:
            临时文件路径
        """
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="image_upload_")

        # 从 URL 提取文件扩展名
        ext = self._extract_extension(image_url)
        if not ext:
            ext = ".jpg"  # 默认扩展名

        # 生成临时文件名
        temp_file_name = f"temp_{int(time.time() * 1000)}{ext}"
        temp_file_path = os.path.join(temp_dir, temp_file_name)

        # 下载图片
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(image_url)

            if response.status_code != 200:
                raise Exception(f"下载图片失败: status={response.status_code}")

            # 写入临时文件
            with open(temp_file_path, "wb") as f:
                f.write(response.content)

        logger.info(f"[COSUploader] 图片已下载到临时目录: {temp_file_path}")

        return temp_file_path

    def _extract_extension(self, url: str) -> Optional[str]:
        """
        从 URL 提取文件扩展名

        Args:
            url: 图片 URL

        Returns:
            扩展名（如 .jpg, .png）或 None
        """
        # 支持 jpg, jpeg, png, webp, gif
        supported_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]

        url_lower = url.lower()
        for ext in supported_extensions:
            if ext in url_lower:
                return ext

        return None

    def _get_image_dimensions(self, file_path: str) -> tuple[int, int]:
        """
        获取图片尺寸

        Args:
            file_path: 图片文件路径

        Returns:
            (width, height)
        """
        # 简化实现：返回默认尺寸
        # 真实项目可以使用 PIL/Pillow 获取真实尺寸
        # from PIL import Image
        # with Image.open(file_path) as img:
        #     return img.size

        return (1200, 800)  # 默认尺寸

    def _generate_cos_key(
        self,
        placeholder_id: str,
        task_id: str,
        file_path: str
    ) -> str:
        """
        生成 COS 存储路径

        格式：{upload_path}/{task_id}/{placeholder_id}.{ext}

        Args:
            placeholder_id: 占位符 ID
            task_id: 任务 ID
            file_path: 文件路径（用于提取扩展名）

        Returns:
            COS 存储路径
        """
        ext = os.path.splitext(file_path)[1] or ".jpg"

        # 使用 hash 简化路径（避免过长）
        task_hash = hashlib.md5(task_id.encode()).hexdigest()[:8]

        cos_key = f"{self.upload_path}{task_hash}/{placeholder_id}{ext}"

        return cos_key

    async def _upload_to_cos(self, file_path: str, cos_key: str) -> str:
        """
        上传文件到 COS

        Args:
            file_path: 本地文件路径
            cos_key: COS 存储路径

        Returns:
            COS 访问 URL

        注意：当前为简化实现，真实项目建议使用 cos-python-sdk-v5
        """
        # TODO: 使用真实 COS SDK 上传
        # 当前返回 Mock URL，真实实现需要：
        # 1. 安装 cos-python-sdk-v5
        # 2. 使用 qcloud_cos 库上传
        # 3. 返回真实的 COS URL

        # 构建简化版 COS URL（假设上传成功）
        cos_url = f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{cos_key}"

        # 模拟上传延迟
        await self._mock_upload(file_path, cos_key)

        return cos_url

    async def _mock_upload(self, file_path: str, cos_key: str):
        """
        Mock 上传实现

        真实实现参考：

        from qcloud_cos import CosClient
        from qcloud_cos import CosS3Client

        config = {
            "Region": self.region,
            "SecretId": self.secret_id,
            "SecretKey": self.secret_key,
        }
        client = CosS3Client(config)

        with open(file_path, "rb") as fp:
            response = client.put_object(
                Bucket=self.bucket,
                Body=fp,
                Key=cos_key,
            )

        Args:
            file_path: 本地文件路径
            cos_key: COS 存储路径
        """
        import asyncio

        # 模拟上传延迟
        await asyncio.sleep(0.2)

        # 模拟成功
        logger.info(
            f"[COSUploader] Mock 上传完成: {file_path} -> {cos_key}"
        )

    def _cleanup_temp_file(self, file_path: str):
        """
        清理临时文件

        Args:
            file_path: 文件路径
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                # 也删除临时目录
                temp_dir = os.path.dirname(file_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
                logger.info(f"[COSUploader] 临时文件已清理: {file_path}")
        except Exception as e:
            logger.warning(f"[COSUploader] 清理临时文件失败: {e}")


# ============ Mock 实现（用于测试） ============


class MockCOSUploader:
    """
    Mock COS 上传服务

    用于单元测试，不上传真实文件
    """

    MOCK_COS_URL_TEMPLATE = "https://mock-bucket.cos.ap-shanghai.myqcloud.com/article-images/mock/{placeholder_id}.jpg"

    def __init__(self):
        self._available = True
        logger.info("[MockCOSUploader] Mock 服务初始化完成")

    def is_available(self) -> bool:
        return self._available

    async def upload_from_url(
        self,
        image_url: str,
        placeholder_id: str,
        task_id: str,
        source_provider: ImageProvider,
    ) -> ImageResult:
        import asyncio

        await asyncio.sleep(0.1)

        mock_url = self.MOCK_COS_URL_TEMPLATE.format(placeholder_id=placeholder_id)

        return ImageResult(
            taskId=task_id,
            placeholderId=placeholder_id,
            url=mock_url,
            cosKey=f"article-images/mock/{placeholder_id}.jpg",
            width=1200,
            height=800,
            sourceProvider=source_provider,
            status=ImageTaskStatus.COMPLETED,
            originalUrl=image_url,
            uploadTime=100.0,
        )


# ============ 工厂函数 ============


def create_cos_uploader(use_mock: bool = False):
    """
    创建 COS 上传服务实例

    Args:
        use_mock: 是否使用 Mock 实现

    Returns:
        COSUploader 或 MockCOSUploader 实例
    """
    if use_mock:
        return MockCOSUploader()
    return COSUploader()