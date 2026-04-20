# -*- coding: utf-8 -*-
"""
Seedream API 测试脚本（修复编码问题）
"""

import asyncio
import httpx

# 从 .env 文件中读取的正确配置
API_KEY = "528a9a0d-3896-4b58-ab32-5ada91607621"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
ENDPOINT_ID = "ep-20260410201140-sfnn9"

async def test_seedream():
    print("=" * 70)
    print("Seedream API Test")
    print("=" * 70)
    print(f"\nConfig:")
    print(f"  API Key: {API_KEY[:8]}...{API_KEY[-8:]}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Endpoint ID: {ENDPOINT_ID}")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 测试端点列表
    endpoints = [
        {
            "name": "v3/images/generations (OpenAI compatible)",
            "url": f"{BASE_URL}/images/generations",
            "payload": {
                "model": ENDPOINT_ID or "Doubao-Seedream-5.0-lite",
                "prompt": "A cute cat",
                "size": "1024x1024",
                "n": 1
            }
        },
        {
            "name": "v3/chat/completions (test connection)",
            "url": f"{BASE_URL}/chat/completions",
            "payload": {
                "model": ENDPOINT_ID or "Doubao-Seedream-5.0-lite",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
        }
    ]

    for i, ep in enumerate(endpoints, 1):
        print(f"\n{'=' * 70}")
        print(f"Testing {i}/{len(endpoints)}: {ep['name']}")
        print(f"URL: {ep['url']}")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    ep['url'],
                    headers=headers,
                    json=ep['payload']
                )

                print(f"Status: {response.status_code}")

                if response.status_code == 200:
                    print("SUCCESS!")

                    try:
                        data = response.json()
                        print(f"Response keys: {list(data.keys())}")

                        # 检查图片 URL
                        if "data" in data and len(data["data"]) > 0:
                            url = data["data"][0].get("url", "")
                            if url:
                                print(f"Image URL: {url}")
                                print("\n[OK] Seedream API is working!")
                                return True

                        # 检查聊天响应
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0]["message"]["content"]
                            print(f"Response: {content}")
                            print("\n[OK] Connection successful (chat endpoint)")
                            return True

                        print(f"Response: {str(data)[:500]}")

                    except Exception as e:
                        print(f"Parse error: {e}")
                        print(f"Raw: {response.text[:500]}")

                elif response.status_code == 401:
                    print("[ERROR] Authentication failed")
                    print(f"Details: {response.text[:300]}")

                elif response.status_code == 403:
                    print("[ERROR] Permission denied")
                    print(f"Details: {response.text[:300]}")

                elif response.status_code == 404:
                    print("[ERROR] Endpoint not found")
                    print(f"Details: {response.text[:300]}")

                elif response.status_code == 400:
                    print("[ERROR] Bad request")
                    print(f"Details: {response.text[:300]}")

                else:
                    print(f"[ERROR] Unknown status: {response.status_code}")
                    print(f"Details: {response.text[:300]}")

        except httpx.TimeoutException:
            print("[ERROR] Request timeout")

        except httpx.ConnectError as e:
            print(f"[ERROR] Connection failed: {e}")
            print("  - Check network connection")
            print("  - Check if URL is correct")

        except Exception as e:
            print(f"[ERROR] Exception: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("\n[FAILED] All endpoints failed")
    print("\nSuggestions:")
    print("1. Check Volcengine ARK console:")
    print(f"   - API Key is correct")
    print(f"   - Endpoint ID '{ENDPOINT_ID}' exists and is running")
    print("2. Check API Key permissions:")
    print("   - Has image generation permission")
    print("   - Has sufficient quota/balance")
    print("3. Refer to official docs:")
    print("   - https://www.volcengine.com/docs/82379")

    print("\nNote: System will fallback to Picsum service")
    print("The article generation flow will not be interrupted")
    return False


if __name__ == "__main__":
    try:
        asyncio.run(test_seedream())
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
