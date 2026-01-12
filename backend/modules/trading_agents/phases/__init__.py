"""TradingAgents 四阶段运行器"""

from modules.trading_agents.phases.phase1 import run_phase1
from modules.trading_agents.phases.phase2 import run_phase2
from modules.trading_agents.phases.phase3 import run_phase3
from modules.trading_agents.phases.phase4 import run_phase4

__all__ = [
    "run_phase1",
    "run_phase2",
    "run_phase3",
    "run_phase4",
]
