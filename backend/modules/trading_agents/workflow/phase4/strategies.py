"""
Phase 4: 策略风格与风险评估

**版本**: v4.0 (LangChain 1.1.0 create_agent 重构版)
**最后更新**: 2026-01-15

激进、中性、保守策略分析师，以及风险管理委员会主席。
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from langchain.agents import create_agent


from modules.trading_agents.models.state import (
    WorkflowState,
    PhaseExecution,
    AgentExecution,
    TaskStatus,
)
from modules.trading_agents.config import get_enabled_agents

logger = logging.getLogger(__name__)


# =============================================================================
# 策略分析师基类
# =============================================================================

class StrategyDebator:
    """策略分析师基类"""

    def __init__(
        self,
        model: BaseChatModel,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化策略分析师

        Args:
            model: LLM 模型
            config: 智能体配置
        """
        self.model = model
        self.config = config or {}
        self.slug = config.get("slug", "unknown")
        self.name = config.get("name", "策略分析师")
        self.agent = self._create_agent()

        def _create_agent(self):
        """创建智能体实例 (LangChain 1.1.0 create_agent API)"""
        system_prompt_str = self._build_system_prompt()
        
        # 使用 LangChain 1.1.0 的 create_agent
        graph = create_agent(
            model=self.model,
            tools=[],
            system_prompt=system_prompt_str,
            debug=False
        )
        
        return graph

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        role_definition = self.config.get("roleDefinition", "")

        prompt = f"""
# 角色
你是一名{self.name}，你的任务是{self._get_description()}。

# 职责
{self._get_responsibilities()}

# 输出格式
```markdown
# {self.name}报告

## 核心观点
[一句话总结你的核心观点]

## 分析维度
{self._get_analysis_dimensions()}

## 结论
[基于你的策略风格得出的结论]

## 建议
[具体的投资建议]
```

{role_definition}
"""
        return prompt.strip()

    def _get_description(self) -> str:
        """获取描述"""
        return "进行投资策略分析"

    def _get_responsibilities(self) -> str:
        """获取职责"""
        return "1. 分析投资策略\n2. 评估风险收益\n3. 给出投资建议"

    def _get_analysis_dimensions(self) -> str:
        """获取分析维度"""
        return "- 收益预期\n- 风险评估\n- 投资建议"

    async def analyze(
        self,
        state: WorkflowState,
        investment_decision: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行策略分析

        Args:
            state: 工作流状态
            investment_decision: 投资决策

        Returns:
            分析结果
        """
        logger.info(f"[Phase 4] {self.name}开始分析: {state.stock_code}")

        # 构建输入
        messages = self._build_input_messages(state, investment_decision)
        try:
            # 调用智能体 (使用 LangGraph create_agent 的正确输入格式)
            # 调用智能体
            prompt_text = messages[0]["content"] if messages else "Please analyze."
            result = await self.agent.ainvoke({"messages": [{"role": "user", "content": prompt_text}]}, config={"recursion_limit": 10})

            # 提取输出
            output = self._extract_output(result)

            logger.info(f"[Phase 4] {self.name}分析完成: {state.stock_code}")

            return {
                "slug": self.slug,
                "name": self.name,
                "output": output,
                "error": None
            }

        except Exception as e:
            logger.error(f"[Phase 4] {self.name}分析失败: {state.stock_code}, error={e}")

            return {
                "slug": self.slug,
                "name": self.name,
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
请以{self.name}的视角，评估以下投资决策：

# 股票信息
- 股票代码: {state.stock_code}
- 股票名称: {state.stock_name or '未知'}
- 市场: {state.market}
- 交易日期: {state.trade_date}

{decision_text}

请提供你的策略分析和建议。
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


# =============================================================================
# 具体策略分析师
# =============================================================================

class AggressiveDebator(StrategyDebator):
    """激进策略分析师"""

    def _get_description(self) -> str:
        return "追求高收益，承担高波动"

    def _get_responsibilities(self) -> str:
        return """
1. 关注机会成本：踏空的风险
2. 关注潜在收益：上涨空间的乐观预期
3. 关注时间效率：快速获利的可能性
"""

    def _get_analysis_dimensions(self) -> str:
        return """
- **机会成本**: 如果不买入，可能错失的收益
- **潜在收益**: 乐观情景下的上涨空间
- **时间效率**: 快速获利的可能性
- **波动容忍**: 高波动下的持仓能力
"""


class NeutralDebator(StrategyDebator):
    """中性策略分析师"""

    def _get_description(self) -> str:
        return "风险收益平衡，优化夏普比率"

    def _get_responsibilities(self) -> str:
        return """
1. 波动率控制：适度的风险敞口
2. 风险调整收益：最大化夏普比率
3. 分散化投资：降低单一资产风险
"""

    def _get_analysis_dimensions(self) -> str:
        return """
- **波动率**: 适度的风险敞口
- **夏普比率**: 风险调整后的收益
- **分散化**: 降低组合风险
- **平衡配置**: 收益与风险的平衡
"""


class ConservativeDebator(StrategyDebator):
    """保守策略分析师"""

    def _get_description(self) -> str:
        return "本金安全优先，防御性资产配置"

    def _get_responsibilities(self) -> str:
        return """
1. 下行保护：最大回撤控制
2. 股息率：稳定的现金流回报
3. 估值安全：足够的安全边际
"""

    def _get_analysis_dimensions(self) -> str:
        return """
- **下行保护**: 最大回撤控制
- **股息率**: 稳定的现金流
- **估值安全**: 安全边际
- **本金安全**: 防御性资产配置
"""


# =============================================================================
# 风险管理委员会主席
# =============================================================================

class RiskManager:
    """
    风险管理委员会主席

    综合评估风险，行使一票否决权。
    """

    def __init__(
        self,
        model: BaseChatModel,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化风险管理委员会主席

        Args:
            model: LLM 模型
            config: 智能体配置
        """
        self.model = model
        self.config = config or {}
        self.agent = self._create_agent()

        def _create_agent(self):
        """创建智能体实例 (LangChain 1.1.0 create_agent API)"""
        system_prompt_str = self._build_system_prompt()
        
        # 使用 LangChain 1.1.0 的 create_agent
        graph = create_agent(
            model=self.model,
            tools=[],
            system_prompt=system_prompt_str,
            debug=False
        )
        
        return graph

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        role_definition = self.config.get("roleDefinition", "")

        prompt = f"""
# 角色
你是风险管理委员会主席，你的任务是综合评估投资风险，并行使一票否决权。

# 职责
1. 评估整体风险水平（低/中/高）
2. 识别关键风险点
3. 给出风险控制建议
4. 在风险过高时行使否决权

# 推荐等级定义
- **STRONG_BUY**: 预期显著上涨，强烈推荐买入
- **BUY**: 预期上涨，推荐买入
- **HOLD**: 维持现有仓位
- **SELL**: 预期下跌，建议卖出
- **STRONG_SELL**: 预期显著下跌，强烈建议卖出

# 风险等级定义
- **LOW**: 低风险，本金安全性高
- **MEDIUM**: 中等风险，正常波动范围
- **HIGH**: 高风险，存在较大本金损失风险

# 输出格式
```markdown
# 风险评估报告

## 整体风险评级
**风险等级**: LOW / MEDIUM / HIGH
**是否批准**: ✅ 批准 / ❌ 否决

## 关键风险点
### 风险 1
- 描述
- 影响程度
- 应对措施

## 风险控制建议
[具体的风险控制措施]

## 最终推荐
**推荐等级**: STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
**目标价位**: 买入 ¥XX.XX, 卖出 ¥XX.XX

## 结论
[综合风险评估结论]
```

{role_definition}
"""
        return prompt.strip()

    async def assess(
        self,
        state: WorkflowState,
        strategy_reports: List[Dict[str, Any]],
        investment_decision: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行风险评估

        Args:
            state: 工作流状态
            strategy_reports: 策略报告列表
            investment_decision: 投资决策

        Returns:
            评估结果
        """
        logger.info(f"[Phase 4] 风险管理委员会主席开始评估: {state.stock_code}")

        # 构建输入
        messages = self._build_input_messages(state, strategy_reports, investment_decision)
        try:
            # 调用智能体 (使用 LangGraph create_agent 的正确输入格式)
            # 调用智能体
            prompt_text = messages[0]["content"] if messages else "Please analyze."
            result = await self.agent.ainvoke({"messages": [{"role": "user", "content": prompt_text}]}, config={"recursion_limit": 10})

            # 提取输出
            output = self._extract_output(result)

            # 解析决策
            decision = self._parse_decision(output)

            logger.info(
                f"[Phase 4] 风险管理委员会主席评估完成: {state.stock_code}, "
                f"批准: {decision.get('approved') if decision else 'N/A'}"
            )

            return {
                "output": output,
                "decision": decision,
                "error": None
            }

        except Exception as e:
            logger.error(f"[Phase 4] 风险管理委员会主席评估失败: {state.stock_code}, error={e}")

            return {
                "output": None,
                "decision": None,
                "error": str(e)
            }

    def _build_input_messages(
        self,
        state: WorkflowState,
        strategy_reports: List[Dict[str, Any]],
        investment_decision: Optional[Dict[str, Any]]
    ) -> list:
        """构建输入消息"""
        # 构建策略报告摘要
        reports_summary = "\n\n".join([
            f"## {report['name']}\n{report['output']}"
            for report in strategy_reports
            if report.get("output")
        ])

        decision_text = ""
        if investment_decision:
            decision_text = f"""
# 初始投资决策
- 推荐等级: {investment_decision.get('recommendation')}
- 风险等级: {investment_decision.get('risk_level')}
- 买入价位: {investment_decision.get('buy_price')}
- 卖出价位: {investment_decision.get('sell_price')}
"""

        prompt = f"""
请综合评估以下投资策略和决策：

# 股票信息
- 股票代码: {state.stock_code}
- 股票名称: {state.stock_name or '未知'}
- 市场: {state.market}
- 交易日期: {state.trade_date}

{decision_text}

# 策略分析师报告
{reports_summary}

请提供你的风险评估和最终推荐。
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

    def _parse_decision(self, output: Optional[str]) -> Optional[Dict[str, Any]]:
        """解析决策结果"""
        if not output:
            return None

        import re
        import json

        # 检查是否批准
        approved = None
        if "否决" in output or "❌" in output:
            approved = False
        elif "批准" in output or "✅" in output:
            approved = True

        # 提取推荐等级
        recommendation = None
        for rec in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]:
            if rec in output.upper():
                recommendation = rec
                break

        # 提取风险等级
        risk_level = None
        for risk in ["LOW", "MEDIUM", "HIGH"]:
            if risk in output.upper():
                risk_level = risk
                break

        if recommendation or approved is not None:
            return {
                "approved": approved if approved is not None else True,
                "recommendation": recommendation,
                "risk_level": risk_level
            }

        return None


# =============================================================================
# Phase 4 执行函数
# =============================================================================

async def execute_phase4(
    state: WorkflowState,
    model: BaseChatModel,
    config: Dict[str, Any]
) -> WorkflowState:
    """
    执行 Phase 4: 策略风格与风险评估

    Args:
        state: 工作流状态
        model: LLM 模型
        config: 智能体配置

    Returns:
        更新后的工作流状态
    """
    logger.info(f"[Phase 4] 开始执行, 任务ID: {state.task_id}")

    # 更新状态
    state.current_phase = 4
    state.status = TaskStatus.RUNNING

    # 检查阶段是否启用
    phase4_config = config.get("phase4", {})
    if not phase4_config.get("enabled", True):
        logger.warning("[Phase 4] 阶段未启用，跳过")
        state.status = TaskStatus.COMPLETED
        state.progress = 100.0
        state.completed_at = datetime.utcnow()
        return state

    # 获取智能体配置
    agents_config = get_enabled_agents(config, "phase4")

    # 创建智能体实例
    debators = []
    risk_manager = None

    for agent_config in agents_config:
        slug = agent_config["slug"]
        if slug == "aggressive-debator":
            debators.append(AggressiveDebator(model, agent_config))
        elif slug == "neutral-debator":
            debators.append(NeutralDebator(model, agent_config))
        elif slug == "conservative-debator":
            debators.append(ConservativeDebator(model, agent_config))
        elif slug == "risk-manager":
            risk_manager = RiskManager(model, agent_config)

    if not debators:
        logger.warning("[Phase 4] 没有策略分析师")

    if not risk_manager:
        logger.error("[Phase 4] 缺少风险管理委员会主席")
        state.status = TaskStatus.FAILED
        state.error_message = "缺少风险管理委员会主席"
        return state

    # 创建阶段执行记录
    phase4_execution = PhaseExecution(
        phase=4,
        phase_name="策略风格与风险评估",
        started_at=datetime.utcnow(),
        execution_mode="serial",
        max_concurrency=1
    )

    # 执行策略分析师
    strategy_reports = []
    for debator in debators:
        result = await debator.analyze(state, state.investment_decision)
        strategy_reports.append(result)
        state.strategy_reports.append({
            "slug": result["slug"],
            "name": result["name"],
            "content": result["output"],
            "timestamp": datetime.utcnow().isoformat()
        })

    # 执行风险管理委员会主席
    manager_result = await risk_manager.assess(state, strategy_reports, state.investment_decision)

    # 更新状态
    if manager_result.get("decision"):
        decision = manager_result["decision"]
        state.risk_approval = decision

        # 更新最终推荐（风险经理可以否决或调整）
        if decision.get("recommendation"):
            state.final_recommendation = decision["recommendation"]
        if decision.get("risk_level"):
            state.risk_level = decision["risk_level"]

    # 更新执行记录
    phase4_execution.completed_at = datetime.utcnow()
    phase4_execution.status = TaskStatus.COMPLETED

    # 添加智能体执行记录
    for debator in debators:
        phase4_execution.agents.append(
            AgentExecution(
                slug=debator.slug,
                name=debator.name,
                started_at=phase4_execution.started_at,
                completed_at=phase4_execution.completed_at,
                status=TaskStatus.COMPLETED
            )
        )

    phase4_execution.agents.append(
        AgentExecution(
            slug="risk-manager",
            name="风险管理委员会主席",
            started_at=phase4_execution.started_at,
            completed_at=phase4_execution.completed_at,
            status=TaskStatus.COMPLETED
        )
    )

    state.phase_executions.append(phase4_execution)

    # 更新进度
    state.progress = 100.0
    state.status = TaskStatus.COMPLETED
    state.completed_at = datetime.utcnow()

    logger.info(f"[Phase 4] 完成, 最终推荐: {state.final_recommendation}")

    return state
