"""
Phase 3: 交易执行策划

**版本**: v3.2 (LangChain create_tool_calling_agent 重构版)
**最后更新**: 2026-01-15

专业交易员，制定具体的交易执行计划。
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from langchain_core.language_models import BaseChatModel
from langchain.agents import create_agent


from modules.trading_agents.models.state import (
    WorkflowState,
    PhaseExecution,
    TaskStatus,
)
from modules.trading_agents.config import get_enabled_agents
from modules.trading_agents.workflow.callbacks import WebSocketCallbackHandler

logger = logging.getLogger(__name__)


class Trader:
    """
    专业交易员

    制定具体的交易执行计划。
    """

    def __init__(
        self,
        model: BaseChatModel,
        config: Optional[Dict[str, Any]] = None,
        task_id: str = None,
        websocket_manager: Any = None,
    ):
        """
        初始化交易员

        Args:
            model: LLM 模型
            config: 智能体配置
            task_id: 任务 ID（用于回调推送）
            websocket_manager: WebSocket 管理器实例
        """
        self.model = model
        self.config = config or {}
        self.task_id = task_id
        self.websocket_manager = websocket_manager
        # 创建回调处理器
        self.callbacks = []
        if self.task_id and self.websocket_manager:
            self.callbacks.append(WebSocketCallbackHandler(
                task_id=self.task_id,
                agent_slug="trader",
                agent_name="交易员",
                websocket_manager=self.websocket_manager,
            ))
        self.agent = self._create_agent()

    def _create_agent(self):
        """创建智能体实例 (LangChain 1.1.0 create_agent API)"""
        system_prompt_str = self._build_system_prompt()
        # 使用 LangChain 1.1.0 的 create_agent
        # 注意: callbacks 不能在这里传递，需要在 ainvoke 时通过 config 传递
        graph = create_agent(
            model=self.model,
            tools=[],
            system_prompt=system_prompt_str,
            debug=False,
        )
        return graph

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        role_definition = self.config.get("roleDefinition", "")

        prompt = f"""
# 角色
你是一名专业交易员，你的任务是基于投资决策制定具体的交易执行计划。

# 职责
1. 分析当前市场流动性
2. 制定挂单策略（限价/市价/分批）
3. 选择合适的算法交易（VWAP/TWAP）
4. 制定应急预案（突发跳水/流动性枯竭）

# 工作流程
1. 阅读投资决策报告
2. 分析市场流动性（成交量、买卖价差）
3. 根据目标价位和风险等级制定执行策略
4. 选择合适的订单类型和算法
5. 制定风险控制措施

# 禁止事项
- 禁止给出投资建议（买入/卖出），这是投资组合经理的职责
- 你的职责是"如何执行"，而不是"是否执行"

# 输出格式
```markdown
# 交易执行计划

## 市场流动性分析
- 当前成交量
- 买卖价差
- 流动性评估

## 挂单策略
### 买入方案
- 订单类型: [限价/市价/条件单]
- 执行方式: [一次性/分批/算法]
- 目标价位: ¥XX.XX
- 数量: XX股

### 卖出方案
- 止损价位: ¥XX.XX
- 止盈价位: ¥XX.XX
- 执行方式

## 算法交易选择
- VWAP (成交量加权平均价)
- TWAP (时间加权平均价)
- 冰山订单 (隐藏大单)
- 其他: __

## 风险控制
- 滑点容忍度: X%
- 单笔最大量: XX股
- 日内最大量: XX股

## 应急预案
### 场景1: 突发跳水
- 应对措施
- 触发条件

### 场景2: 流动性枯竭
- 应对措施
- 触发条件
```

{role_definition}
"""
        return prompt.strip()

    async def plan(
        self,
        state: WorkflowState,
        investment_decision: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        制定交易执行计划

        Args:
            state: 工作流状态
            investment_decision: 投资决策

        Returns:
            执行计划结果
        """
        logger.info(f"[Phase 3] 交易员开始制定计划: {state.stock_code}")

        # 构建输入
        messages = self._build_input_messages(state, investment_decision)
        try:
            # 调用智能体 (使用 LangGraph create_agent 的正确输入格式)
            prompt_text = messages[0]["content"] if messages else "Please analyze."
            # 通过 config 传递 callbacks
            config = {"recursion_limit": 10}
            if self.callbacks:
                from langchain_core.callbacks import CallbackManager
                config["configurable"] = {"callbacks": CallbackManager(self.callbacks)}
            result = await self.agent.ainvoke({"messages": [{"role": "user", "content": prompt_text}]}, config=config)

            # 提取输出
            output = self._extract_output(result)

            logger.info(f"[Phase 3] 交易员计划完成: {state.stock_code}")

            return {
                "output": output,
                "error": None
            }

        except Exception as e:
            logger.error(f"[Phase 3] 交易员计划失败: {state.stock_code}, error={e}")

            return {
                "output": None,
                "error": str(e)
            }

    def _build_input_messages(
        self,
        state: WorkflowState,
        investment_decision: Optional[Dict[str, Any]]
    ) -> list:
        """构建输入消息"""
        decision_text = ""
        if investment_decision:
            decision_text = f"""
# 投资决策
- 推荐等级: {investment_decision.get('recommendation')}
- 风险等级: {investment_decision.get('risk_level')}
- 买入价位: {investment_decision.get('buy_price')}
- 卖出价位: {investment_decision.get('sell_price')}
"""

        prompt = f"""
请基于以下投资决策，制定交易执行计划：

# 股票信息
- 股票代码: {state.stock_code}
- 股票名称: {state.stock_name or '未知'}
- 市场: {state.market}
- 交易日期: {state.trade_date}

{decision_text}

请提供详细的交易执行计划。
"""
        return [{"role": "user", "content": prompt.strip()}]

    def _extract_output(self, result: Any) -> Optional[str]:
        """从结果中提取输出"""
        if isinstance(result, dict):
            # AgentExecutor format: {"output": "..."}
            output = result.get("output")
            if output:
                return str(output)

            # LangGraph format
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, "content"):
                    return last_message.content
                elif isinstance(last_message, dict):
                    return last_message.get("content")

        if isinstance(result, str):
            return result

        return str(result)


async def execute_phase3(
    state: WorkflowState,
    model: BaseChatModel,
    config: Dict[str, Any]
) -> WorkflowState:
    """
    执行 Phase 3: 交易执行策划

    Args:
        state: 工作流状态
        model: LLM 模型
        config: 智能体配置

    Returns:
        更新后的工作流状态
    """
    logger.info(f"[Phase 3] 开始执行, 任务ID: {state.task_id}")

    # 更新状态
    state.current_phase = 3
    state.status = TaskStatus.RUNNING

    # 检查阶段是否启用
    phase3_config = config.get("phase3", {})
    if not phase3_config.get("enabled", True):
        logger.warning("[Phase 3] 阶段未启用，跳过")
        state.progress = 75.0  # Phase 3 完成后进度 75%
        return state

    # 获取智能体配置
    agents_config = get_enabled_agents(config, "phase3")

    # 创建交易员
    trader = None
    for agent_config in agents_config:
        if agent_config["slug"] == "trader":
            trader = Trader(model, agent_config)
            break

    if not trader:
        logger.error("[Phase 3] 缺少交易员智能体")
        state.status = TaskStatus.FAILED
        state.error_message = "缺少交易员智能体"
        return state

    # 创建阶段执行记录
    phase3_execution = PhaseExecution(
        phase=3,
        phase_name="交易执行策划",
        started_at=datetime.now(timezone.utc),
        execution_mode="serial",
        max_concurrency=1
    )

    # 执行交易员计划
    result = await trader.plan(state, state.investment_decision)

    # 更新状态
    if result["output"]:
        state.trading_plan = {
            "content": result["output"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # 更新执行记录
    phase3_execution.completed_at = datetime.now(timezone.utc)
    phase3_execution.status = TaskStatus.COMPLETED if not result["error"] else TaskStatus.FAILED

    state.phase_executions.append(phase3_execution)

    # 更新进度
    state.progress = 75.0  # Phase 3 完成后进度 75%

    logger.info(f"[Phase 3] 完成")

    return state
