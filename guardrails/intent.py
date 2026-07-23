"""Нормализованное представление предлагаемого действия.

Движок ничего не знает ни про блокчейн, ни про мессенджеры.
Адаптеры приводят свою реальность к Intent — и только.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any


class Actor(str, Enum):
    """Кто предлагает действие."""

    AGENT = "agent"  # ИИ действует от имени пользователя (кошелёк)
    COUNTERPARTY = "counterparty"  # кто-то действует на пользователя (страж)
    USER = "user"  # пользователь сам, просит проверить


class Action(str, Enum):
    """Тип действия. Список расширяется адаптерами."""

    TRANSFER = "transfer"
    SIGN_CONTRACT = "sign_contract"
    APPROVE_ALLOWANCE = "approve_allowance"
    VISIT_LINK = "visit_link"
    INBOUND_MESSAGE = "inbound_message"
    INBOUND_CALL = "inbound_call"


class ArtifactKind(str, Enum):
    """Артефакты — то, что участвует в схеме.

    Сознательно отсутствует: личность, соцсети, фото, связи.
    Проверяем то, что участвует в схеме, а не того, кто по ту сторону.
    """

    ADDRESS = "address"
    CONTRACT = "contract"
    DOMAIN = "domain"
    URL = "url"
    PHONE = "phone"
    TEXT = "text"


@dataclass(frozen=True)
class Artifact:
    kind: ArtifactKind
    value: str
    # Внешние сигналы, подтянутые адаптером (возраст домена, репорты и т.п.).
    # Правила читают отсюда, чтобы ядро оставалось без сетевых зависимостей.
    facts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Intent:
    actor: Actor
    action: Action
    artifacts: tuple[Artifact, ...] = ()
    amount: Decimal | None = None
    currency: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    intent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def artifacts_of(self, kind: ArtifactKind) -> tuple[Artifact, ...]:
        return tuple(a for a in self.artifacts if a.kind == kind)
