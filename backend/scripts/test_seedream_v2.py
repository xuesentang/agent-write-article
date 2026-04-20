# -*- coding: utf-8 -*-
"""
Seedream API Test V2 - Fix size parameter
"""

import asyncio
import httpx

API_KEY = "528a9a0d-3896-4b58-ab32-5ada91607621"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
ENDPOINT_ID = "ep-20260410201140-sfnn9"

async def test_seedream():
    print("=" * 70)
    print("Seedream API Test V2")
    print("=" * 70)
    print(f"\nConfig:")
    print(f"  API Key: {API_KEY[:8]}...{API_KEY[-8:]}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Endpoint ID: {ENDPOINT_ID}")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 最小要求：3686400 像素 = 1920x1920 或 2048x1800 等
    test_sizes = [
        "2048x2048",  # 4194304 像素
        "1920x1920",  # 3686400 像素（最小要求）
        "2560x1440",  # 3686400 像素（16:9）
    ]

    for size in test_sizes:
        print(f"\n{'=' * 70}")
        print(f"Testing with size: {size}")
        print(f"Pixels: {int(size.split('x')[0]) * int(size.split('x')[1])}")

        payload = {
            "model": ENDPOINT_ID,
            "prompt": "A cute cat sitting on a windowsill, high quality, detailed",
            "size": size,
            "n": 1
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{BASE_URL}/images/generations",
                    headers=headers,
                    json=payload
                )

                print(f"Status: {response.status_code}")

                if response.status_code == 200:
                    print("[SUCCESS]!")
                    try:
                        data = response.json()
                        print(f"Response: {str(data)[:500]}")

                        if "data" in data and len(data["data"]) > 0:
                            url = data["data"][0].get("url", "")
                            if url:
                                print(f"\nImage URL: {url}")
                                print("\n[OK] Seedream API is working correctly!")
                                print(f"  API Key: Valid")
                                print(f"  Endpoint: {ENDPOINT_ID} - Running and accessible")
                                print(f"  Image Generation: Functional")
                                return True

                    except Exception as e:
                        print(f"Parse error: {e}")

                elif response.status_code == 400:
                    print("[ERROR] Bad request")
                    print(f"Details: {response.text[:400]}")

                else:
                    print(f"[ERROR] Status {response.status_code}")
                    print(f"Details: {response.text[:400]}")

        except Exception as e:
            print(f"[ERROR] {e}")

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("\n[FAILED] Image generation failed with all sizes")
    return False


if __name__ == "__main__":
    asyncio.run(test_seedream())
