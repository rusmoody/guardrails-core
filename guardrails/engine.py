"""Движок вердикта.

Порядок жёсткий и намеренный:

1. Конверт лимитов. Нарушен — дальше не идём, всегда спрашиваем человека.
2. Правила собирают сигналы.
3. Сигналы сворачиваются в score.
4. Пороги дают решение.
5. Уровень автономии решает, спрашивать ли внутри конверта.
6. Всё пишется в лог.

LLM в этой цепочке не участвует. Модель предлагает Intent — и всё.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Sequence

from .audit import AuditRecord, AuditSink, InMemorySink
from .intent import Actor, Intent
from .policy import Autonomy, Policy
from .rules import Rule
from .verdict import Decision, Signal, Verdict


def combine(signals: Sequence[Signal]) -> float:
    """Вероятностное объединение: 1 - Π(1 - severity).

    Много слабых сигналов накапливаются, но score никогда не достигает 1.0 —
    сознательно, чтобы система не выдавала абсолютных утверждений.
    """
    acc = 1.0
    for signal in signals:
        acc *= 1.0 - signal.severity
    return 1.0 - acc


class Engine:
    def __init__(
        self,
        rules: Iterable[Rule],
        policy: Policy | None = None,
        sink: AuditSink | None = None,
    ) -> None:
        self.rules = tuple(rules)
        self.policy = policy or Policy()
        self.sink = sink or InMemorySink()

    def evaluate(self, intent: Intent, spent_today: Decimal = Decimal(0)) -> Verdict:
        reasons: list[str] = []

        # 1. Жёсткий слой. Не пробивается ни правилами, ни уровнем автономии.
        violations = self.policy.envelope.violations(intent, spent_today)

        # 2-3. Мягкий слой.
        signals: list[Signal] = []
        for rule in self.rules:
            if rule.applies_to(intent):
                signals.extend(rule.evaluate(intent))
        score = combine(signals)

        # 4. Пороги.
        if score >= self.policy.block_threshold:
            decision = Decision.BLOCK
            reasons.append(f"score {score:.2f} выше порога блокировки")
        elif score >= self.policy.confirm_threshold:
            decision = Decision.CONFIRM
            reasons.append(f"score {score:.2f} выше порога подтверждения")
        else:
            decision = Decision.ALLOW

        # 5. Конверт важнее автономии.
        if violations:
            if decision is not Decision.BLOCK:
                decision = Decision.CONFIRM
            reasons.extend(violations)
        elif (
            decision is Decision.ALLOW
            and intent.actor is Actor.AGENT
            and self.policy.autonomy is Autonomy.NORMAL
        ):
            # Уровень автономии касается только действий агента от нашего имени.
            # К входящим проверкам он неприменим: страж не дёргает человека
            # на каждом чистом сообщении.
            decision = Decision.CONFIRM
            reasons.append("обычный уровень автономии — подтверждаем вручную")

        verdict = Verdict(
            intent_id=intent.intent_id,
            decision=decision,
            score=score,
            signals=tuple(signals),
            reasons=tuple(reasons),
        )

        # 6.
        self.sink.write(AuditRecord.build(intent, verdict))
        return verdict
