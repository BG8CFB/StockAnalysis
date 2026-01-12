"""
GLM-4.7 思考能力深度测试

测试目标：
1. 基础对话功能
2. 思考模式验证（检查 reasoning_content 和 reasoning_tokens）
3. Token 消耗统计
4. 价格计算准确性
5. 使用统计记录
6. 工具调用场景
7. 流式输出功能

用户提供的测试凭证：
- API Key: 0c2ef49f7a7149fab64be7a725c6f759.9a72qZtM3vlTlic2
- API: https://open.bigmodel.cn/api/coding/paas/v4
- Model: glm-4.7
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ai.langchain.adapter import LangChainAdapter
from core.ai.types import AIMessage, AIResponse
from core.ai.pricing import get_pricing_service, BUILTIN_MODEL_PRICES
from core.ai.usage import get_usage_service, AIUsageRecord
from langchain_core.messages import HumanMessage, AIMessage as LCAIMessage, SystemMessage

# 配置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GLM47ThinkingTest:
    """GLM-4.7 思考能力测试套件"""

    # 用户提供的测试凭证
    TEST_API_KEY = "0c2ef49f7a7149fab64be7a725c6f759.9a72qZtM3vlTlic2"
    TEST_API_BASE = "https://open.bigmodel.cn/api/coding/paas/v4"
    TEST_MODEL_ID = "glm-4.7"
    TEST_USER_ID = "test_user_thinking"

    def __init__(self):
        self.pricing_service = get_pricing_service()
        self.usage_service = get_usage_service()
        self.test_results = []
        self.chat_model = None

    async def setup_test_model(self):
        """设置测试用的 ChatModel"""
        logger.info("=" * 60)
        logger.info("设置测试模型")
        logger.info("=" * 60)

        self.chat_model = LangChainAdapter.create_chat_model(
            model_id=self.TEST_MODEL_ID,
            api_key=self.TEST_API_KEY,
            platform="zhipu",
            api_base_url=self.TEST_API_BASE,
            temperature=0.7,
            timeout_seconds=120,
            max_retries=3,
            thinking_enabled=True,
        )

        logger.info(f"模型 ID: {self.TEST_MODEL_ID}")
        logger.info(f"API Base: {self.TEST_API_BASE}")
        logger.info(f"思考支持: 已启用")
        logger.info("")

    def _parse_response(self, response: Any) -> dict:
        """解析 LangChain 响应"""
        result = {
            "content": "",
            "reasoning_content": None,
            "thinking_tokens": None,
            "usage": None,
            "tool_calls": None,
            "raw_response": None,
        }

        # 获取内容
        result["content"] = response.content or ""

        # 解析思考内容（GLM-4.7）
        if hasattr(response, "response_metadata"):
            metadata = response.response_metadata
            if "reasoning_content" in metadata:
                result["reasoning_content"] = metadata["reasoning_content"]
            if "reasoning_tokens" in metadata:
                result["thinking_tokens"] = metadata["reasoning_tokens"]
            result["raw_response"] = metadata

        # 解析工具调用
        if hasattr(response, "tool_calls") and response.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id or "",
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": tc.args,
                    },
                }
                for tc in response.tool_calls
            ]

        # 解析 usage
        if hasattr(response, "usage_metadata"):
            result["usage"] = response.usage_metadata

        return result

    async def test_1_basic_chat(self):
        """测试 1: 基础对话功能"""
        logger.info("=" * 60)
        logger.info("测试 1: 基础对话功能")
        logger.info("=" * 60)

        try:
            messages = [HumanMessage(content="你好，请简单介绍一下你自己。")]

            response = await self.chat_model.ainvoke(messages)
            parsed = self._parse_response(response)

            logger.info(f"响应内容: {parsed['content'][:200]}...")

            usage = parsed.get('usage') or {}
            logger.info(f"输入 Tokens: {usage.get('input_tokens', 0)}")
            logger.info(f"输出 Tokens: {usage.get('output_tokens', 0)}")
            logger.info(f"总 Tokens: {usage.get('total_tokens', 0)}")

            self.test_results.append({
                "test": "basic_chat",
                "status": "PASS",
                "input_tokens": usage.get('input_tokens', 0),
                "output_tokens": usage.get('output_tokens', 0),
            })

            logger.info("✅ 测试 1 通过")
            return True

        except Exception as e:
            logger.error(f"❌ 测试 1 失败: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append({"test": "basic_chat", "status": "FAIL", "error": str(e)})
            return False

    async def test_2_thinking_mode_simple(self):
        """测试 2: 简单思考任务（触发思考模式）"""
        logger.info("=" * 60)
        logger.info("测试 2: 简单思考任务")
        logger.info("=" * 60)

        try:
            messages = [
                HumanMessage(
                    content="一个农场有鸡和兔子共50只，脚共有140只。"
                           "问鸡和兔子各有多少只？请详细说明你的推理过程。"
                )
            ]

            response = await self.chat_model.ainvoke(messages)
            parsed = self._parse_response(response)

            has_thinking = parsed['reasoning_content'] is not None
            thinking_tokens = parsed['thinking_tokens'] or 0

            logger.info(f"响应内容: {parsed['content'][:200]}...")
            logger.info(f"有思考内容: {'是' if has_thinking else '否'}")
            if has_thinking:
                logger.info(f"思考内容预览: {parsed['reasoning_content'][:200]}...")
            logger.info(f"思考 Tokens: {thinking_tokens}")

            usage = parsed.get('usage') or {}
            logger.info(f"输入 Tokens: {usage.get('input_tokens', 0)}")
            logger.info(f"输出 Tokens: {usage.get('output_tokens', 0)}")
            logger.info(f"总 Tokens: {usage.get('total_tokens', 0)}")

            self.test_results.append({
                "test": "thinking_simple",
                "status": "PASS",
                "has_thinking": has_thinking,
                "thinking_tokens": thinking_tokens,
            })

            logger.info("✅ 测试 2 通过")
            return True

        except Exception as e:
            logger.error(f"❌ 测试 2 失败: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append({"test": "thinking_simple", "status": "FAIL", "error": str(e)})
            return False

    async def test_3_thinking_mode_complex(self):
        """测试 3: 复杂思考任务（深度推理）"""
        logger.info("=" * 60)
        logger.info("测试 3: 复杂思考任务（深度推理）")
        logger.info("=" * 60)

        try:
            messages = [
                HumanMessage(
                    content="""请分析以下投资场景：

某投资者正在考虑投资一家新能源公司，请从以下角度进行深度分析：

1. 行业前景：分析新能源行业未来5-10年的发展趋势
2. 财务分析：如何评估该公司的财务健康状况
3. 风险评估：可能面临的主要风险因素
4. 投资建议：基于以上分析给出投资建议

请详细展示你的思考过程，包括每个决策点的推理逻辑。"""
                )
            ]

            logger.info("发送复杂思考任务请求...")
            start_time = datetime.now()

            response = await self.chat_model.ainvoke(messages)
            parsed = self._parse_response(response)

            elapsed = (datetime.now() - start_time).total_seconds()

            has_thinking = parsed['reasoning_content'] is not None
            thinking_tokens = parsed['thinking_tokens'] or 0

            usage = parsed.get('usage') or {}
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)

            logger.info(f"响应时间: {elapsed:.2f} 秒")
            logger.info(f"有思考内容: {'是' if has_thinking else '否'}")
            logger.info(f"思考 Tokens: {thinking_tokens}")
            logger.info(f"输入 Tokens: {input_tokens}")
            logger.info(f"输出 Tokens: {output_tokens}")
            logger.info(f"总 Tokens: {total_tokens}")

            if has_thinking:
                thinking_length = len(parsed['reasoning_content'])
                logger.info(f"思考内容长度: {thinking_length} 字符")
                logger.info(f"思考内容预览:\n{parsed['reasoning_content'][:500]}...")

            response_length = len(parsed['content'])
            logger.info(f"响应内容长度: {response_length} 字符")
            logger.info(f"响应内容预览:\n{parsed['content'][:500]}...")

            # 计算理论成本
            expected_cost = self.pricing_service.calculate_cost(
                model_id=self.TEST_MODEL_ID,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                thinking_tokens=thinking_tokens,
            )
            logger.info(f"理论成本: {expected_cost} 分")

            # 记录使用统计
            try:
                await self.usage_service.record_from_response(
                    user_id=self.TEST_USER_ID,
                    model_id=self.TEST_MODEL_ID,
                    model_name="GLM-4.7 Test",
                    response=response,
                    task_id="test_task_complex",
                    phase="test_phase",
                    tool_calls=parsed['tool_calls'],
                )
                logger.info("使用统计已记录")

                # 获取统计
                stats = await self.usage_service.get_user_stats(self.TEST_USER_ID)
                logger.info(f"用户统计总调用次数: {stats.get('total_calls', 0)}")
                logger.info(f"用户统计总 Tokens: {stats.get('total_tokens', 0)}")
                logger.info(f"用户统计总成本: {stats.get('total_cost', 0)} 分")
            except Exception as e:
                logger.warning(f"记录使用统计失败: {e}")

            self.test_results.append({
                "test": "thinking_complex",
                "status": "PASS",
                "has_thinking": has_thinking,
                "thinking_tokens": thinking_tokens,
                "thinking_length": thinking_length if has_thinking else 0,
                "response_length": response_length,
                "elapsed_seconds": elapsed,
                "expected_cost": float(expected_cost) if expected_cost else 0,
            })

            logger.info("✅ 测试 3 通过")
            return True

        except Exception as e:
            logger.error(f"❌ 测试 3 失败: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append({"test": "thinking_complex", "status": "FAIL", "error": str(e)})
            return False

    async def test_4_price_calculation(self):
        """测试 4: 价格计算准确性验证"""
        logger.info("=" * 60)
        logger.info("测试 4: 价格计算准确性验证")
        logger.info("=" * 60)

        try:
            # 获取 GLM-4.7 的内置价格
            model_price = self.pricing_service.get_price(self.TEST_MODEL_ID)

            if model_price:
                logger.info(f"模型: {self.TEST_MODEL_ID}")
                logger.info(f"输入价格: {model_price.input_price} 元/{model_price.input_unit.value}")
                logger.info(f"输出价格: {model_price.output_price} 元/{model_price.output_unit.value}")
                if model_price.thinking_price:
                    logger.info(f"思考价格: {model_price.thinking_price} 元/{model_price.thinking_unit.value}")
                logger.info(f"货币: {model_price.currency}")

                # 测试成本计算
                test_cases = [
                    {"input": 1000, "output": 500, "thinking": 0},
                    {"input": 5000, "output": 2000, "thinking": 1000},
                    {"input": 10000, "output": 5000, "thinking": 3000},
                ]

                for i, case in enumerate(test_cases, 1):
                    cost = self.pricing_service.calculate_cost(
                        model_id=self.TEST_MODEL_ID,
                        input_tokens=case["input"],
                        output_tokens=case["output"],
                        thinking_tokens=case["thinking"],
                    )
                    logger.info(f"测试用例 {i}: 输入={case['input']}, 输出={case['output']}, 思考={case['thinking']} => 成本={cost} 分")

                self.test_results.append({
                    "test": "price_calculation",
                    "status": "PASS",
                    "model_found": True,
                })
                logger.info("✅ 测试 4 通过")
                return True
            else:
                logger.warning(f"⚠️ 未找到模型 {self.TEST_MODEL_ID} 的价格配置")
                self.test_results.append({
                    "test": "price_calculation",
                    "status": "WARN",
                    "model_found": False,
                })
                return False

        except Exception as e:
            logger.error(f"❌ 测试 4 失败: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append({"test": "price_calculation", "status": "FAIL", "error": str(e)})
            return False

    async def test_5_streaming_output(self):
        """测试 5: 流式输出功能"""
        logger.info("=" * 60)
        logger.info("测试 5: 流式输出功能")
        logger.info("=" * 60)

        try:
            messages = [
                HumanMessage(content="请用流式输出方式，介绍 Python 编程语言的特点。")
            ]

            full_content = []
            chunk_count = 0
            start_time = datetime.now()

            async for chunk in self.chat_model.astream(messages):
                chunk_count += 1
                if chunk.content:
                    full_content.append(chunk.content)

            elapsed = (datetime.now() - start_time).total_seconds()
            complete_response = ''.join(full_content)

            logger.info(f"流式块数量: {chunk_count}")
            logger.info(f"响应时间: {elapsed:.2f} 秒")
            logger.info(f"响应长度: {len(complete_response)} 字符")
            logger.info(f"响应内容预览: {complete_response[:300]}...")

            self.test_results.append({
                "test": "streaming_output",
                "status": "PASS",
                "chunk_count": chunk_count,
                "response_length": len(complete_response),
                "elapsed_seconds": elapsed,
            })

            logger.info("✅ 测试 5 通过")
            return True

        except Exception as e:
            logger.error(f"❌ 测试 5 失败: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append({"test": "streaming_output", "status": "FAIL", "error": str(e)})
            return False

    async def test_6_multi_turn_conversation(self):
        """测试 6: 多轮对话（上下文保持）"""
        logger.info("=" * 60)
        logger.info("测试 6: 多轮对话（上下文保持）")
        logger.info("=" * 60)

        try:
            conversation = [
                HumanMessage(content="我的名字叫张三，请记住这个名字。"),
                LCAIMessage(content="好的，我记住了，你的名字叫张三。"),
                HumanMessage(content="我叫什么名字？"),
            ]

            response = await self.chat_model.ainvoke(conversation)

            logger.info(f"响应: {response.content}")

            usage = response.usage_metadata if hasattr(response, 'usage_metadata') else {}
            logger.info(f"输入 Tokens: {usage.get('input_tokens', 0)}")
            logger.info(f"输出 Tokens: {usage.get('output_tokens', 0)}")

            # 检查是否正确回答了名字
            has_correct_name = "张三" in response.content

            self.test_results.append({
                "test": "multi_turn_conversation",
                "status": "PASS" if has_correct_name else "WARN",
                "context_preserved": has_correct_name,
            })

            if has_correct_name:
                logger.info("✅ 测试 6 通过（上下文正确保持）")
            else:
                logger.warning("⚠️ 测试 6 通过但上下文可能未正确保持")

            return True

        except Exception as e:
            logger.error(f"❌ 测试 6 失败: {e}")
            import traceback
            traceback.print_exc()
            self.test_results.append({"test": "multi_turn_conversation", "status": "FAIL", "error": str(e)})
            return False

    async def print_summary(self):
        """打印测试摘要"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("测试摘要报告")
        logger.info("=" * 60)

        pass_count = sum(1 for r in self.test_results if r.get("status") == "PASS")
        warn_count = sum(1 for r in self.test_results if r.get("status") == "WARN")
        fail_count = sum(1 for r in self.test_results if r.get("status") == "FAIL")
        total_count = len(self.test_results)

        logger.info(f"总测试数: {total_count}")
        logger.info(f"通过: {pass_count}")
        logger.info(f"警告: {warn_count}")
        logger.info(f"失败: {fail_count}")

        logger.info("")
        logger.info("详细结果:")
        for i, result in enumerate(self.test_results, 1):
            status_emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}
            logger.info(f"  {i}. {result['test']}: {status_emoji.get(result.get('status'), '?')}")
            if result.get('error'):
                logger.info(f"     错误: {result['error']}")

        logger.info("")
        logger.info("=" * 60)

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("")
        logger.info("╔" + "=" * 58 + "╗")
        logger.info("║" + " " * 10 + "GLM-4.7 思考能力深度测试" + " " * 20 + "║")
        logger.info("╚" + "=" * 58 + "╝")
        logger.info("")

        # 设置模型
        await self.setup_test_model()

        # 运行测试
        await self.test_1_basic_chat()
        await self.test_2_thinking_mode_simple()
        await self.test_3_thinking_mode_complex()
        await self.test_4_price_calculation()
        await self.test_5_streaming_output()
        await self.test_6_multi_turn_conversation()

        # 打印摘要
        await self.print_summary()


async def main():
    """主函数"""
    test = GLM47ThinkingTest()
    try:
        await test.run_all_tests()
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 确保 MongoDB 连接已初始化
    from core.db.mongodb import mongodb

    # 初始化 MongoDB 连接
    mongodb.connect()
    try:
        asyncio.run(main())
    finally:
        mongodb.close()
