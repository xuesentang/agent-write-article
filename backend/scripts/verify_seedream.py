"""
验证 Seedream 文生图 API 是否正常工作
"""

import asyncio
import httpx
import sys
import os

# 确保能找到app模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.image.providers.seedream_service import SeedreamService


async def test_seedream_config():
    """测试 Seedream 配置"""
    print("=" * 60)
    print("1. 检查 Seedream 配置")
    print("=" * 60)

    print(f"API Key: {settings.SEEDREAM_API_KEY}")
    print(f"API Key 长度: {len(settings.SEEDREAM_API_KEY)} 字符")
    print(f"Base URL: {settings.SEEDREAM_BASE_URL}")
    print(f"Endpoint ID: {settings.SEEDREAM_ENDPOINT_ID}")

    if not settings.SEEDREAM_API_KEY:
        print("\n❌ SEEDREAM_API_KEY 未配置!")
        return False

    if settings.SEEDREAM_API_KEY == "your_seedream_api_key_here":
        print("\n❌ SEEDREAM_API_KEY 使用的是占位符，请填写真实值!")
        return False

    print("\n✅ Seedream 配置已就绪")
    return True


async def test_seedream_service_init():
    """测试 Seedream 服务初始化"""
    print("\n" + "=" * 60)
    print("2. 测试 Seedream 服务初始化")
    print("=" * 60)

    try:
        service = SeedreamService()
        print(f"服务类型: {service.__class__.__name__}")
        print(f"服务名称: {service.get_provider_name().value}")
        print(f"服务可用: {service.is_available()}")

        if not service.is_available():
            print("\n❌ Seedream 服务初始化失败，标记为不可用")
            return False

        print("\n✅ Seedream 服务初始化成功")
        return True

    except Exception as e:
        print(f"\n❌ Seedream 服务初始化异常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_seedream_api_direct():
    """直接测试 Seedream API 调用"""
    print("\n" + "=" * 60)
    print("3. 直接测试 Seedream API 调用")
    print("=" * 60)

    api_key = settings.SEEDREAM_API_KEY
    base_url = settings.SEEDREAM_BASE_URL
    endpoint_id = settings.SEEDREAM_ENDPOINT_ID

    # 构建 API 地址
    # 根据火山引擎 ARK 文档，图片生成端点通常是：
    # /v3/images/generations (OpenAI 兼容)
    # 或直接使用推理端点

    endpoints_to_try = [
        # OpenAI 兼容格式
        f"{base_url}/images/generations",
        f"{base_url}/v3/images/generations",

        # 直接调用推理端点
        f"https://ark.cn-beijing.volces.com/api/v3/chat/completions",  # 用于测试连接性

        # 其他可能的端点
        f"https://ark.cn-beijing.volces.com/v3/images/generations",
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print(f"将尝试以下端点:")
    for i, url in enumerate(endpoints_to_try, 1):
        print(f"  {i}. {url}")

    print(f"\n请求头 Authorization: Bearer {api_key[:8]}...")
    print(f"Endpoint ID: {endpoint_id}")

    # 先尝试一个简单的连接测试
    test_urls = [
        endpoints_to_try[0],  # 首选
        endpoints_to_try[2],  # 聊天接口（测试连接）
    ]

    for test_url in test_urls:
        print(f"\n尝试连接: {test_url}")

        try:
            # 构建请求载荷
            if "chat" in test_url:
                # 聊天接口测试
                payload = {
                    "model": endpoint_id or "Doubao-Seedream-5.0-lite",
                    "messages": [{"role": "user", "content": "你好"}],
                    "max_tokens": 10
                }
            else:
                # 图片生成接口
                payload = {
                    "model": endpoint_id or "Doubao-Seedream-5.0-lite",
                    "prompt": "测试图片：一只可爱的猫咪",
                    "size": "1024x1024"
                }

            print(f"请求载荷: {payload}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    test_url,
                    headers=headers,
                    json=payload
                )

                print(f"响应状态码: {response.status_code}")
                print(f"响应头: {dict(response.headers)}")

                if response.status_code == 200:
                    print(f"✅ API 调用成功!")
                    print(f"响应内容（前500字符）: {response.text[:500]}")
                    return True
                elif response.status_code == 401:
                    print(f"❌ 认证失败: {response.text[:200]}")
                    print("   请检查 API Key 是否正确")
                elif response.status_code == 404:
                    print(f"❌ 端点不存在: {response.text[:200]}")
                elif response.status_code == 400:
                    print(f"❌ 请求参数错误: {response.text[:200]}")
                elif response.status_code == 429:
                    print(f"❌ 请求频率超限: {response.text[:200]}")
                else:
                    print(f"⚠️  未知错误: {response.text[:200]}")

        except httpx.TimeoutException:
            print(f"⚠️  请求超时")
        except httpx.ConnectError as e:
            print(f"❌ 连接失败: {e}")
        except Exception as e:
            print(f"❌ 异常: {e}")
            import traceback
            traceback.print_exc()

    print("\n所有端点尝试失败")
    return False


async def test_seedream_service_call():
    """测试 Seedream 服务调用"""
    print("\n" + "=" * 60)
    print("4. 测试 Seedream 服务调用（通过服务层）")
    print("=" * 60)

    try:
        service = SeedreamService()

        print("尝试生成图片...")
        print("关键词: 猫咪、可爱、宠物")
        print("图片类型: photo")
        print("尺寸: 1024x1024")

        result = await service.fetch_image(
            keywords=["猫咪", "可爱", "宠物"],
            image_type="photo",
            width=1024,
            height=1024,
            context="一只可爱的小猫咪",
        )

        print(f"\n生成结果:")
        print(f"  成功: {result.success}")
        print(f"  URL: {result.url}")
        print(f"  提供商: {result.provider.value}")

        if result.success:
            print(f"  宽度: {result.width}")
            print(f"  高度: {result.height}")
            print(f"  源ID: {result.sourceId}")
            if result.meta:
                print(f"  元数据: {result.meta}")

            # 检查是否是备用 URL（Picsum）
            if "picsum.photos" in result.url:
                print("\n⚠️  注意: 返回的是 Picsum 备用 URL，说明 Seedream 调用失败")
                print("   这是容错机制，流程不会中断，但文生图功能未正常工作")
            else:
                print("\n✅ Seedream 文生图调用成功!")
                return True
        else:
            print(f"\n❌ Seedream 调用失败: {result.error}")
            return False

    except Exception as e:
        print(f"\n❌ Seedream 服务调用异常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有验证测试"""
    print("\n" + "=" * 60)
    print("Seedream 文生图 API 验证测试")
    print("=" * 60)

    # 1. 检查配置
    config_ok = await test_seedream_config()
    if not config_ok:
        print("\n❌ 配置检查失败，测试终止")
        return

    # 2. 测试服务初始化
    init_ok = await test_seedream_service_init()
    if not init_ok:
        print("\n❌ 服务初始化失败，后续测试跳过")
        return

    # 3. 直接测试 API 调用
    api_ok = await test_seedream_api_direct()

    # 4. 测试服务层调用
    service_ok = await test_seedream_service_call()

    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"配置检查: {'✅' if config_ok else '❌'}")
    print(f"服务初始化: {'✅' if init_ok else '❌'}")
    print(f"API 直接调用: {'✅' if api_ok else '❌'}")
    print(f"服务层调用: {'✅' if service_ok else '❌'}")

    if config_ok and init_ok and api_ok and service_ok:
        print("\n🎉 Seedream 文生图 API 工作正常!")
    elif config_ok and init_ok and not api_ok and not service_ok:
        print("\n⚠️  Seedream API 调用失败")
        print("   可能的原因:")
        print("   1. API Key 不正确或已过期")
        print("   2. Endpoint ID 未部署或已停止")
        print("   3. API 端点地址不正确")
        print("   4. 网络连接问题")
        print("\n   建议:")
        print("   1. 检查火山引擎 ARK 控制台确认 API Key 和端点状态")
        print("   2. 确认端点 ID 是否正确且处于运行状态")
        print("   3. 查看火山引擎 ARK 文档确认正确的 API 调用方式")
        print("\n   注: 系统会自动降级到 Picsum 兜底服务，整体流程不会中断")
    else:
        print("\n⚠️  部分测试失败，请检查配置")


if __name__ == "__main__":
    asyncio.run(main())
