"""
简化版 Seedream API 测试脚本
直接读取 .env 文件并测试 API 调用
"""

import asyncio
import httpx
import os
from pathlib import Path

# 读取 .env 文件
def load_env():
    """读取 .env 文件"""
    env_path = Path(__file__).parent.parent / ".env"
    env_vars = {}

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            # 解析 key=value
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    return env_vars


async def test_seedream_api():
    """测试 Seedream API 调用"""
    print("=" * 70)
    print("Seedream 文生图 API 测试")
    print("=" * 70)

    # 加载环境变量
    env = load_env()

    api_key = env.get('SEEDREAM_API_KEY', '')
    base_url = env.get('SEEDREAM_BASE_URL', '')
    endpoint_id = env.get('SEEDREAM_ENDPOINT_ID', '')

    print(f"\n配置信息:")
    print(f"  API Key: {api_key[:8]}...{api_key[-8:] if len(api_key) > 16 else ''} (长度: {len(api_key)})")
    print(f"  Base URL: {base_url}")
    print(f"  Endpoint ID: {endpoint_id}")

    if not api_key:
        print("\n❌ SEEDREAM_API_KEY 未配置!")
        return False

    if not base_url:
        print("\n❌ SEEDREAM_BASE_URL 未配置!")
        return False

    # 要尝试的 API 端点列表
    # 根据火山引擎 ARK 文档和 OpenAI 兼容接口规范
    endpoints_to_try = [
        {
            "name": "OpenAI 兼容 - images/generations (base_url)",
            "url": f"{base_url}/images/generations",
            "payload": {
                "model": endpoint_id or "Doubao-Seedream-5.0-lite",
                "prompt": "测试图片：一只可爱的小猫咪",
                "size": "1024x1024",
                "n": 1
            }
        },
        {
            "name": "OpenAI 兼容 - v3/images/generations",
            "url": f"{base_url}/images/generations",
            "payload": {
                "model": endpoint_id or "Doubao-Seedream-5.0-lite",
                "prompt": "测试图片：一只可爱的小猫咪",
                "size": "1024x1024",
                "n": 1
            }
        },
        {
            "name": "火山引擎 ARK - v3/images/generations (官方域名)",
            "url": "https://ark.cn-beijing.volces.com/api/v3/images/generations",
            "payload": {
                "model": endpoint_id or "Doubao-Seedream-5.0-lite",
                "prompt": "测试图片：一只可爱的小猫咪",
                "size": "1024x1024",
                "n": 1
            }
        },
        {
            "name": "火山引擎 ARK - chat/completions (测试连接性)",
            "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            "payload": {
                "model": endpoint_id or "Doubao-Seedream-5.0-lite",
                "messages": [{"role": "user", "content": "你好，请回复：测试成功"}],
                "max_tokens": 10
            }
        },
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 尝试每个端点
    for i, endpoint in enumerate(endpoints_to_try, 1):
        print(f"\n{'=' * 70}")
        print(f"尝试 {i}/{len(endpoints_to_try)}: {endpoint['name']}")
        print(f"{'=' * 70}")
        print(f"URL: {endpoint['url']}")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    endpoint['url'],
                    headers=headers,
                    json=endpoint['payload']
                )

                print(f"状态码: {response.status_code}")

                if response.status_code == 200:
                    print(f"✅ API 调用成功!")

                    # 解析响应
                    try:
                        data = response.json()
                        print(f"响应结构: {list(data.keys())}")

                        # 检查是否有图片 URL
                        if "data" in data and len(data["data"]) > 0:
                            image_url = data["data"][0].get("url", "")
                            if image_url:
                                print(f"图片 URL: {image_url}")
                                print(f"\n🎉 Seedream 文生图 API 工作正常!")
                                return True

                        # 其他可能的响应格式
                        if "images" in data and len(data["images"]) > 0:
                            image_url = data["images"][0].get("url", "")
                            if image_url:
                                print(f"图片 URL: {image_url}")
                                print(f"\n🎉 Seedream 文生图 API 工作正常!")
                                return True

                        if "url" in data:
                            print(f"图片 URL: {data['url']}")
                            print(f"\n🎉 Seedream 文生图 API 工作正常!")
                            return True

                        # 聊天接口的响应
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0]["message"]["content"]
                            print(f"响应内容: {content}")
                            print(f"\n✅ API 连接成功（测试的是聊天接口）")
                            return True

                        print(f"\n响应完整内容（前500字符）: {str(data)[:500]}")

                    except Exception as e:
                        print(f"解析响应失败: {e}")
                        print(f"原始响应: {response.text[:500]}")

                elif response.status_code == 401:
                    print(f"❌ 认证失败")
                    print(f"响应内容: {response.text[:300]}")
                    print("\n可能原因:")
                    print("  - API Key 不正确")
                    print("  - API Key 已过期")
                    print("  - API Key 权限不足")

                elif response.status_code == 403:
                    print(f"❌ 权限不足")
                    print(f"响应内容: {response.text[:300]}")
                    print("\n可能原因:")
                    print("  - API Key 无调用图片生成接口的权限")
                    print("  - Endpoint ID 不属于当前 API Key")

                elif response.status_code == 404:
                    print(f"❌ 端点不存在")
                    print(f"响应内容: {response.text[:300]}")
                    print("\n可能原因:")
                    print("  - 端点地址不正确")
                    print("  - Endpoint ID 不存在")

                elif response.status_code == 400:
                    print(f"❌ 请求参数错误")
                    print(f"响应内容: {response.text[:300]}")
                    print("\n可能原因:")
                    print("  - model 参数不正确")
                    print("  - prompt 或其他参数格式错误")

                elif response.status_code == 429:
                    print(f"❌ 请求频率超限")
                    print(f"响应内容: {response.text[:300]}")

                else:
                    print(f"⚠️  未知错误")
                    print(f"响应内容: {response.text[:300]}")

        except httpx.TimeoutException:
            print(f"⚠️  请求超时（60秒）")

        except httpx.ConnectError as e:
            print(f"❌ 连接失败: {e}")
            print("\n可能原因:")
            print("  - 网络连接问题")
            print("  - API 地址不正确")

        except Exception as e:
            print(f"❌ 异常: {e}")
            import traceback
            traceback.print_exc()

    # 所有尝试都失败
    print(f"\n{'=' * 70}")
    print("测试结果总结")
    print(f"{'=' * 70}")
    print(f"\n❌ 所有端点尝试失败")

    print(f"\n📋 建议检查项:")
    print(f"1. 火山引擎 ARK 控制台确认:")
    print(f"   - API Key 是否正确且有效")
    print(f"   - Endpoint ID '{endpoint_id}' 是否存在且处于运行状态")
    print(f"   - Endpoint 是否支持图片生成功能")
    print(f"2. 确认 API Key 权限:")
    print(f"   - 是否有调用图片生成接口的权限")
    print(f"   - 是否有足够的余额/配额")
    print(f"3. 参考火山引擎 ARK 官方文档:")
    print(f"   - https://www.volcengine.com/docs/82379")

    print(f"\n💡 容错机制:")
    print(f"   - 系统会自动降级到 Picsum 兜底服务")
    print(f"   - 整体文章生成流程不会中断")
    print(f"   - 但会失去 AI 文生图的定制化能力")

    return False


if __name__ == "__main__":
    try:
        result = asyncio.run(test_seedream_api())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试异常: {e}")
        import traceback
        traceback.print_exc()
