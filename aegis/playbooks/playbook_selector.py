"""Maps a regime + CRO stance to a concrete, permitted set of Bitget
GetAgent Playbooks. Aegis never invents a strategy -- it only turns
existing Playbooks on/off and constrains their size/leverage."""

from dataclasses import dataclass

import yaml

from aegis.governance.cro_engine import GovernanceDecision, TradeStance
from aegis.regime.regime_detector import Regime


@dataclass
class PlaybookActivation:
    playbooks: list[str]
    max_position_size_pct: float
    max_leverage: int


class PlaybookSelector:
    def __init__(self, playbook_mapping_path: str = "config/playbook_mapping.yaml"):
        with open(playbook_mapping_path) as f:
            self.mapping = yaml.safe_load(f)

    def select(self, regime: Regime, decision: GovernanceDecision) -> PlaybookActivation:
        if decision.stance == TradeStance.PAUSE:
            return PlaybookActivation(playbooks=[], max_position_size_pct=0.0, max_leverage=1)

        cfg = self.mapping[regime.value]
        size_cap = cfg["max_position_size_pct"]
        if decision.stance == TradeStance.REDUCE:
            size_cap = size_cap * 0.5

        return PlaybookActivation(
            playbooks=cfg["playbooks"],
            max_position_size_pct=size_cap,
            max_leverage=min(decision.max_leverage, cfg["max_leverage"]),
        )
