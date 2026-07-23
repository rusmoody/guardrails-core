"""Демонстрация движка на живых сценариях.

Запуск:  python demo.py
"""

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from guardrails import (
    Action,
    Actor,
    Artifact,
    ArtifactKind,
    Autonomy,
    DEFAULT_GUARDIAN_RULES,
    DEFAULT_WALLET_RULES,
    Decision,
    Engine,
    Envelope,
    InMemorySink,
    Intent,
    Policy,
)

LABEL = {
    Decision.ALLOW: "ПРОПУСКАЕМ",
    Decision.CONFIRM: "СПРАШИВАЕМ ЧЕЛОВЕКА",
    Decision.BLOCK: "БЛОКИРУЕМ",
}


def show(title: str, verdict) -> None:
    print(f"\n{'─' * 68}")
    print(f"  {title}")
    print(f"{'─' * 68}")
    print(f"  Решение: {LABEL[verdict.decision]}   (score {verdict.score:.2f})")
    print(f"\n{verdict.explanation}")
    if verdict.reasons:
        print("\n  Почему именно так:")
        for reason in verdict.reasons:
            print(f"    - {reason}")


# ══════════════════════════════════════════════════════════════════
print("\n\n########  СТРАЖ: входящие сообщения  ########")
# ══════════════════════════════════════════════════════════════════

sink = InMemorySink()
guardian = Engine(DEFAULT_GUARDIAN_RULES, Policy(), sink)

show(
    "1. Обычное сообщение от знакомого",
    guardian.evaluate(
        Intent(
            actor=Actor.COUNTERPARTY,
            action=Action.INBOUND_MESSAGE,
            artifacts=(Artifact(ArtifactKind.TEXT, "Привет! Скинь адрес, я подъеду"),),
        )
    ),
)

show(
    "2. Классика: «служба безопасности банка»",
    guardian.evaluate(
        Intent(
            actor=Actor.COUNTERPARTY,
            action=Action.INBOUND_MESSAGE,
            artifacts=(
                Artifact(
                    ArtifactKind.TEXT,
                    "Служба безопасности! Ваш счёт заблокирован. Срочно "
                    "переведите на безопасный счёт и подтвердите код. Никому не сообщайте!",
                ),
                Artifact(ArtifactKind.DOMAIN, "sber-secure24.top", {"domain_age_days": 2}),
            ),
            context={"payment_channel": "wire"},
        )
    ),
)

show(
    "3. Пограничный: ссылка на свежий домен, без давления",
    guardian.evaluate(
        Intent(
            actor=Actor.COUNTERPARTY,
            action=Action.INBOUND_MESSAGE,
            artifacts=(
                Artifact(ArtifactKind.TEXT, "Смотри какой проект запустили"),
                Artifact(ArtifactKind.URL, "new-defi-yield.io", {"domain_age_days": 12}),
            ),
        )
    ),
)

show(
    "4. Адрес кошелька из реестров жалоб",
    guardian.evaluate(
        Intent(
            actor=Actor.USER,
            action=Action.TRANSFER,
            artifacts=(
                Artifact(ArtifactKind.ADDRESS, "0x9f2b...c41e", {"scam_reports": 7}),
            ),
        )
    ),
)

# ══════════════════════════════════════════════════════════════════
print("\n\n########  КОШЕЛЁК: агент предлагает транзакции  ########")
# ══════════════════════════════════════════════════════════════════

policy_adv = Policy(
    envelope=Envelope(per_tx_cap=Decimal(100), daily_cap=Decimal(500)),
    autonomy=Autonomy.ADVANCED,
)
policy_norm = Policy(envelope=policy_adv.envelope, autonomy=Autonomy.NORMAL)


def transfer(amount, seen=True):
    return Intent(
        actor=Actor.AGENT,
        action=Action.TRANSFER,
        amount=Decimal(amount),
        currency="USDC",
        artifacts=(Artifact(ArtifactKind.ADDRESS, "0xaave...pool", {"seen_before": seen}),),
    )


show(
    "5. Продвинутый уровень, 40 USDC знакомому контракту",
    Engine(DEFAULT_WALLET_RULES, policy_adv, sink).evaluate(transfer(40)),
)

show(
    "6. Обычный уровень, та же транзакция",
    Engine(DEFAULT_WALLET_RULES, policy_norm, sink).evaluate(transfer(40)),
)

show(
    "7. Продвинутый уровень, но 900 USDC — конверт не пробивается",
    Engine(DEFAULT_WALLET_RULES, policy_adv, sink).evaluate(transfer(900)),
)

show(
    "8. Продвинутый, 90 USDC, но за день уже потрачено 450 из 500",
    Engine(DEFAULT_WALLET_RULES, policy_adv, sink).evaluate(
        transfer(90), spent_today=Decimal(450)
    ),
)

# ══════════════════════════════════════════════════════════════════
print(f"\n\n{'═' * 68}")
print(f"  ЛОГ РЕШЕНИЙ — записано {len(sink.records)} шт.")
print(f"{'═' * 68}\n")
for record in sink.records:
    print(f"  {record.decision:8} score={record.score:<6} {record.action:16} {record.artifacts}")
print()
