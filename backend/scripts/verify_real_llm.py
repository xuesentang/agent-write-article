"""
验证真实LLM调用是否正常工作
"""

import asyncio
import sys
import os

# 确保能找到app模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.llm_service import RealLLMService, get_llm_service
from app.agents import TitleAgent, TitleAgentInput


async def test_config_loaded():
    """测试配置是否正确加载"""
    print("=" * 50)
    print("1. 检查配置加载情况")
    print("=" * 50)

    config = settings.get_llm_config("qianwen")
    print(f"默认LLM提供商: {settings.DEFAULT_LLM_PROVIDER}")
    print(f"千问API Key: {config['api_key'][:20]}... (已截断)")
    print(f"千问Base URL: {config['base_url']}")
    print(f"千问Model: {config['model']}")

    config_zhipu = settings.get_llm_config("zhipu")
    print(f"\n智谱API Key: {config_zhipu['api_key'][:20]}... (已截断)")
    print(f"智谱Base URL: {config_zhipu['base_url']}")
    print(f"智谱Model: {config_zhipu['model']}")

    assert config['api_key'], "千问API Key未配置!"
    assert config_zhipu['api_key'], "智谱API Key未配置!"
    print("\n✅ 配置加载正常")


async def test_real_llm_call():
    """测试真实LLM调用"""
    print("\n" + "=" * 50)
    print("2. 测试真实LLM调用 (千问)")
    print("=" * 50)

    service = RealLLMService(provider="qianwen")

    try:
        # 简单测试调用
        response = await service.call(
            prompt="请用一句话回复：你好",
            max_tokens=50,
        )
        print(f"LLM响应: {response}")
        print("\n✅ 千问LLM调用成功!")

    except Exception as e:
        print(f"❌ 千问LLM调用失败: {e}")
        return False

    return True


async def test_zhipu_call():
    """测试智谱LLM调用"""
    print("\n" + "=" * 50)
    print("3. 测试智谱LLM调用")
    print("=" * 50)

    service = RealLLMService(provider="zhipu")

    try:
        response = await service.call(
            prompt="请用一句话回复：你好",
            max_tokens=50,
        )
        print(f"LLM响应: {response}")
        print("\n✅ 智谱LLM调用成功!")

    except Exception as e:
        print(f"❌ 智谱LLM调用失败: {e}")
        return False

    return True


async def test_title_agent_real():
    """测试TitleAgent使用真实LLM"""
    print("\n" + "=" * 50)
    print("4. 测试TitleAgent使用真实LLM生成标题")
    print("=" * 50)

    # 创建不使用mock的TitleAgent
    agent = TitleAgent(use_mock=False, llm_provider="qianwen")

    input_data = TitleAgentInput(
        topic="自媒体爆款文章写作技巧",
        style="专业",
        extra_description="面向新手",
        count=3,  # 只生成3个标题，节省token
    )

    print(f"输入选题: {input_data.topic}")
    print(f"输入风格: {input_data.style}")

    try:
        # 收集流式输出
        stream_content = []

        async def callback(chunk):
            stream_content.append(chunk)
            print(chunk, end="", flush=True)

        output = await agent.execute(input_data, stream_callback=callback)

        print("\n\n生成的标题:")
        for i, title in enumerate(output.titles, 1):
            print(f"{i}. {title.title}")
            if title.reasoning:
                print(f"   推荐理由: {title.reasoning}")

        print(f"\n✅ TitleAgent真实LLM调用成功! 共生成 {len(output.titles)} 个标题")

        # 检查调用日志
        log = agent.get_last_call_log()
        if log:
            print(f"\n调用日志: provider={log['provider']}, success={log['success']}, latency={log['latency_ms']:.2f}ms")

        return True

    except Exception as e:
        print(f"\n❌ TitleAgent调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有验证测试"""
    print("\n" + "=" * 60)
    print("真实LLM集成验证测试")
    print("=" * 60)

    # 1. 检查配置
    await test_config_loaded()

    # 2. 测试千问
    qianwen_ok = await test_real_llm_call()

    # 3. 测试智谱
    zhipu_ok = await test_zhipu_call()

    # 4. 测试TitleAgent
    if qianwen_ok:
        agent_ok = await test_title_agent_real()
    else:
        print("\n跳过TitleAgent测试（千问调用失败）")
        agent_ok = False

    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"配置加载: ✅")
    print(f"千问LLM: {'✅' if qianwen_ok else '❌'}")
    print(f"智谱LLM: {'✅' if zhipu_ok else '❌'}")
    print(f"TitleAgent: {'✅' if agent_ok else '❌'}")

    if qianwen_ok and zhipu_ok and agent_ok:
        print("\n🎉 所有测试通过! 真实LLM已正确接入!")
        print("运行时将默认使用真实大模型(千问)，不会使用Mock模式。")
    else:
        print("\n⚠️ 部分测试失败，请检查API配置或网络连接")


if __name__ == "__main__":
    asyncio.run(main())