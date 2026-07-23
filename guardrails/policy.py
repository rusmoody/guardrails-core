"""Два независимых слоя.

Envelope  — сколько вообще можно. Жёсткие правила, действуют всегда.
Autonomy  — спрашивать ли подтверждение ВНУТРИ конверта.

Продвинутый уровень не означает "безлимит". Он означает
"не дёргаю по мелочи в рамках дозволенного".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from .intent import Action, Intent


class Autonomy(str, Enum):
    NORMAL = "normal"  # спрашивает перед каждым действием
    ADVANCED = "advanced"  # молча исполняет внутри конверта


@dataclass(frozen=True)
class Envelope:
    per_tx_cap: Decimal | None = None
    daily_cap: Decimal | None = None
    allowed_actions: frozenset[Action] | None = None  # None = любые
    allowlist: frozenset[str] = frozenset()  # адреса/домены вне подозрений
    denylist: frozenset[str] = frozenset()

    def violations(self, intent: Intent, spent_today: Decimal) -> list[str]:
        """Что из конверта нарушено. Пустой список = внутри конверта."""
        out: list[str] = []

        if self.allowed_actions is not None and intent.action not in self.allowed_actions:
            out.append(f"действие {intent.action.value} не разрешено политикой")

        for artifact in intent.artifacts:
            if artifact.value in self.denylist:
                out.append(f"{artifact.value} в чёрном списке")

        if intent.amount is not None:
            if self.per_tx_cap is not None and intent.amount > self.per_tx_cap:
                out.append(f"сумма {intent.amount} выше лимита на операцию {self.per_tx_cap}")
            if self.daily_cap is not None and spent_today + intent.amount > self.daily_cap:
                out.append(f"дневной лимит {self.daily_cap} будет превышен")

        return out


@dataclass(frozen=True)
class Policy:
    envelope: Envelope = field(default_factory=Envelope)
    autonomy: Autonomy = Autonomy.NORMAL
    # Пороги по накопленному score сигналов
    confirm_threshold: float = 0.35
    block_threshold: float = 0.75
