"""Лог решений.

Для пользователя — доверие ("что и почему сделал мой агент").
Для заявки — доказательство реальной работы.

Важно: в лог не попадают персональные данные о контрагенте.
Пишем артефакты и сработавшие правила, не личности.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from .intent import Intent
from .verdict import Verdict


@dataclass(frozen=True)
class AuditRecord:
    intent_id: str
    at: str
    actor: str
    action: str
    artifacts: tuple[str, ...]
    decision: str
    score: float
    signals: tuple[dict, ...]
    reasons: tuple[str, ...]
    outcome: str | None = None  # чем кончилось: executed / declined / expired

    @classmethod
    def build(cls, intent: Intent, verdict: Verdict) -> "AuditRecord":
        return cls(
            intent_id=intent.intent_id,
            at=datetime.now(timezone.utc).isoformat(),
            actor=intent.actor.value,
            action=intent.action.value,
            artifacts=tuple(f"{a.kind.value}:{a.value}" for a in intent.artifacts),
            decision=verdict.decision.value,
            score=round(verdict.score, 4),
            signals=tuple(asdict(s) for s in verdict.sorted_signals),
            reasons=verdict.reasons,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@runtime_checkable
class AuditSink(Protocol):
    def write(self, record: AuditRecord) -> None: ...


class InMemorySink:
    """Дефолт для тестов и локального запуска. В проде — Supabase."""

    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def write(self, record: AuditRecord) -> None:
        self.records.append(record)
