"""Результат оценки.

Язык вероятностей, а не вердиктов: движок никогда не утверждает
"безопасно". Максимум — "сигналов риска не найдено", что не одно и то же.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Decision(str, Enum):
    ALLOW = "allow"  # исполняем
    CONFIRM = "confirm"  # спрашиваем человека
    BLOCK = "block"  # не исполняем


@dataclass(frozen=True)
class Signal:
    """Одно наблюдение. Не приговор — вклад в общую картину."""

    code: str
    severity: float  # 0.0 .. 1.0 — насколько тревожно
    explanation: str  # человеческим языком, для показа пользователю
    source: str = "rule"

    def __post_init__(self) -> None:
        if not 0.0 <= self.severity <= 1.0:
            raise ValueError(f"severity вне диапазона 0..1: {self.severity}")


NO_SIGNALS_TEXT = (
    "Явных сигналов риска не найдено. Это не гарантия безопасности — "
    "проверка видит только известные признаки."
)


@dataclass(frozen=True)
class Verdict:
    intent_id: str
    decision: Decision
    score: float
    signals: tuple[Signal, ...] = ()
    reasons: tuple[str, ...] = ()  # почему именно такое решение (политика/пороги)

    @property
    def explanation(self) -> str:
        if not self.signals:
            return NO_SIGNALS_TEXT
        lines = [f"• {s.explanation}" for s in self.sorted_signals]
        return "\n".join(lines)

    @property
    def sorted_signals(self) -> tuple[Signal, ...]:
        return tuple(sorted(self.signals, key=lambda s: s.severity, reverse=True))
