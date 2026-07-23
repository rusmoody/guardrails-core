"""Реализация на Python против общего набора кейсов.

Тот же conformance/cases.json гоняет и JS-порт. Если реализации
разойдутся — здесь или там упадёт тест, а не пользователь.
"""

import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from guardrails import (  # noqa: E402
    Action,
    Actor,
    Artifact,
    ArtifactKind,
    Autonomy,
    DEFAULT_GUARDIAN_RULES,
    DEFAULT_WALLET_RULES,
    Engine,
    Envelope,
    InMemorySink,
    Intent,
    Policy,
)

SUITE = json.loads((ROOT / "conformance" / "cases.json").read_text(encoding="utf-8"))
TOLERANCE = SUITE["tolerance"]
RULE_SETS = {"guardian": DEFAULT_GUARDIAN_RULES, "wallet": DEFAULT_WALLET_RULES}


def build_policy(spec):
    env_spec = spec.get("envelope", {})
    allowed = env_spec.get("allowedActions")
    envelope = Envelope(
        per_tx_cap=Decimal(str(env_spec["perTxCap"])) if "perTxCap" in env_spec else None,
        daily_cap=Decimal(str(env_spec["dailyCap"])) if "dailyCap" in env_spec else None,
        allowed_actions=frozenset(Action(a) for a in allowed) if allowed else None,
        allowlist=frozenset(env_spec.get("allowlist", [])),
        denylist=frozenset(env_spec.get("denylist", [])),
    )
    return Policy(envelope=envelope, autonomy=Autonomy(spec.get("autonomy", "normal")))


def build_intent(spec):
    return Intent(
        actor=Actor(spec["actor"]),
        action=Action(spec["action"]),
        artifacts=tuple(
            Artifact(ArtifactKind(a["kind"]), a["value"], a.get("facts", {}))
            for a in spec.get("artifacts", [])
        ),
        amount=Decimal(str(spec["amount"])) if spec.get("amount") is not None else None,
        currency=spec.get("currency"),
        context=spec.get("context", {}),
    )


class ConformanceTests(unittest.TestCase):
    pass


def make_test(case):
    def test(self):
        engine = Engine(RULE_SETS[case["rules"]], build_policy(case["policy"]), InMemorySink())
        verdict = engine.evaluate(
            build_intent(case["intent"]),
            spent_today=Decimal(str(case.get("spentToday", 0))),
        )
        expect = case["expect"]

        self.assertEqual(verdict.decision.value, expect["decision"], case["description"])

        if "score" in expect:
            self.assertAlmostEqual(verdict.score, expect["score"], delta=TOLERANCE)
        if "scoreBelow" in expect:
            self.assertLess(verdict.score, expect["scoreBelow"])
        if "scoreAbove" in expect:
            self.assertGreater(verdict.score, expect["scoreAbove"])

        codes = sorted(s.code for s in verdict.signals)
        self.assertEqual(codes, sorted(expect["signalCodes"]))

    return test


for _case in SUITE["cases"]:
    setattr(ConformanceTests, f"test_{_case['id']}", make_test(_case))


if __name__ == "__main__":
    unittest.main(verbosity=2)
