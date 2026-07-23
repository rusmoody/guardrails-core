"""Правила.

Правило смотрит на Intent и возвращает сигналы. Оно НЕ принимает решений —
решение собирает движок. Правило не ходит в сеть: всё внешнее приезжает
в Artifact.facts, чтобы ядро осталось без зависимостей и тестировалось.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .intent import Action, Actor, ArtifactKind, Intent
from .verdict import Signal


@runtime_checkable
class Rule(Protocol):
    code: str

    def applies_to(self, intent: Intent) -> bool: ...

    def evaluate(self, intent: Intent) -> list[Signal]: ...


# --------------------------------------------------------------------------
# Правила под стража (скам)
# --------------------------------------------------------------------------


class FreshDomainRule:
    """Свежезарегистрированный домен — классика фишинга."""

    code = "fresh_domain"

    def __init__(self, days_threshold: int = 30) -> None:
        self.days_threshold = days_threshold

    def applies_to(self, intent: Intent) -> bool:
        return bool(intent.artifacts_of(ArtifactKind.DOMAIN) or intent.artifacts_of(ArtifactKind.URL))

    def evaluate(self, intent: Intent) -> list[Signal]:
        out: list[Signal] = []
        for artifact in intent.artifacts:
            age = artifact.facts.get("domain_age_days")
            if age is None or age >= self.days_threshold:
                continue
            severity = 0.6 if age < 7 else 0.4
            out.append(
                Signal(
                    code=self.code,
                    severity=severity,
                    explanation=(
                        f"Домен {artifact.value} зарегистрирован {age} дн. назад. "
                        "Мошеннические сайты обычно живут считаные дни."
                    ),
                )
            )
        return out


class ScamReportsRule:
    """Артефакт встречается в публичных реестрах жалоб."""

    code = "scam_reports"

    def applies_to(self, intent: Intent) -> bool:
        return bool(intent.artifacts)

    def evaluate(self, intent: Intent) -> list[Signal]:
        out: list[Signal] = []
        for artifact in intent.artifacts:
            reports = artifact.facts.get("scam_reports", 0)
            if not reports:
                continue
            severity = min(0.9, 0.3 + 0.1 * reports)
            out.append(
                Signal(
                    code=self.code,
                    severity=severity,
                    explanation=(
                        f"{artifact.value} упоминается в {reports} сообщениях о мошенничестве."
                    ),
                )
            )
        return out


class PressurePatternRule:
    """Давление и срочность — ядро почти любой схемы.

    Смотрим на структуру сообщения, а не на то, кто его прислал.
    """

    code = "pressure_pattern"

    MARKERS = (
        "срочно",
        "немедленно",
        "никому неговори",
        "никому не сообщайте",
        "счёт заблокирован",
        "служба безопасности",
        "подтвердите код",
        "переведите на безопасный счёт",
    )

    def applies_to(self, intent: Intent) -> bool:
        return intent.action in (Action.INBOUND_MESSAGE, Action.INBOUND_CALL)

    def evaluate(self, intent: Intent) -> list[Signal]:
        hits: list[str] = []
        for artifact in intent.artifacts_of(ArtifactKind.TEXT):
            lowered = artifact.value.lower()
            hits.extend(m for m in self.MARKERS if m in lowered)
        if not hits:
            return []
        severity = min(0.85, 0.3 + 0.2 * len(hits))
        return [
            Signal(
                code=self.code,
                severity=severity,
                explanation=(
                    "В сообщении есть признаки давления: "
                    + ", ".join(sorted(set(hits)))
                    + ". Настоящие организации не торопят и не просят коды."
                ),
            )
        ]


class IrreversibleChannelRule:
    """Требование необратимого платежа."""

    code = "irreversible_channel"

    def applies_to(self, intent: Intent) -> bool:
        return intent.actor is Actor.COUNTERPARTY

    def evaluate(self, intent: Intent) -> list[Signal]:
        channel = intent.context.get("payment_channel")
        if channel not in ("gift_card", "crypto", "wire", "p2p_transfer"):
            return []
        return [
            Signal(
                code=self.code,
                severity=0.55,
                explanation=(
                    f"Просят оплату через необратимый канал ({channel}). "
                    "Вернуть такой платёж почти невозможно."
                ),
            )
        ]


# --------------------------------------------------------------------------
# Правила под агентный кошелёк
# --------------------------------------------------------------------------


class UnknownRecipientRule:
    """Агент отправляет средства на адрес без истории взаимодействия."""

    code = "unknown_recipient"

    def applies_to(self, intent: Intent) -> bool:
        return intent.actor is Actor.AGENT and intent.action is Action.TRANSFER

    def evaluate(self, intent: Intent) -> list[Signal]:
        out: list[Signal] = []
        for artifact in intent.artifacts_of(ArtifactKind.ADDRESS):
            if artifact.facts.get("seen_before", False):
                continue
            out.append(
                Signal(
                    code=self.code,
                    severity=0.4,
                    explanation=f"Получатель {artifact.value} раньше не встречался в истории.",
                )
            )
        return out


DEFAULT_GUARDIAN_RULES: tuple[Rule, ...] = (
    FreshDomainRule(),
    ScamReportsRule(),
    PressurePatternRule(),
    IrreversibleChannelRule(),
)

DEFAULT_WALLET_RULES: tuple[Rule, ...] = (
    ScamReportsRule(),
    UnknownRecipientRule(),
)
