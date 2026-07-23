import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guardrails import (  # noqa: E402
    Action,
    Actor,
    Artifact,
    ArtifactKind,
    Autonomy,
    Decision,
    DEFAULT_GUARDIAN_RULES,
    DEFAULT_WALLET_RULES,
    Engine,
    Envelope,
    InMemorySink,
    Intent,
    Policy,
)


class GuardianTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sink = InMemorySink()
        self.engine = Engine(DEFAULT_GUARDIAN_RULES, Policy(), self.sink)

    def test_clean_message_has_no_signals(self) -> None:
        intent = Intent(
            actor=Actor.COUNTERPARTY,
            action=Action.INBOUND_MESSAGE,
            artifacts=(Artifact(ArtifactKind.TEXT, "Привет, как дела?"),),
        )
        verdict = self.engine.evaluate(intent)
        self.assertEqual(verdict.signals, ())
        # Никогда не утверждаем "безопасно".
        self.assertIn("не гарантия", verdict.explanation)

    def test_pressure_and_fresh_domain_stack_up(self) -> None:
        intent = Intent(
            actor=Actor.COUNTERPARTY,
            action=Action.INBOUND_MESSAGE,
            artifacts=(
                Artifact(
                    ArtifactKind.TEXT,
                    "Срочно! Служба безопасности: счёт заблокирован, подтвердите код",
                ),
                Artifact(ArtifactKind.DOMAIN, "bank-secure.top", {"domain_age_days": 2}),
            ),
            context={"payment_channel": "wire"},
        )
        verdict = self.engine.evaluate(intent)
        self.assertEqual(verdict.decision, Decision.BLOCK)
        self.assertGreater(verdict.score, 0.75)

    def test_score_never_reaches_one(self) -> None:
        intent = Intent(
            actor=Actor.COUNTERPARTY,
            action=Action.INBOUND_MESSAGE,
            artifacts=(
                Artifact(ArtifactKind.TEXT, "срочно немедленно служба безопасности"),
                Artifact(ArtifactKind.DOMAIN, "x.top", {"domain_age_days": 1, "scam_reports": 50}),
            ),
        )
        verdict = self.engine.evaluate(intent)
        self.assertLess(verdict.score, 1.0)

    def test_every_evaluation_is_logged(self) -> None:
        intent = Intent(actor=Actor.USER, action=Action.VISIT_LINK)
        self.engine.evaluate(intent)
        self.assertEqual(len(self.sink.records), 1)
        self.assertIn("intent_id", self.sink.records[0].to_json())


class WalletTests(unittest.TestCase):
    def _engine(self, autonomy: Autonomy) -> Engine:
        policy = Policy(
            envelope=Envelope(per_tx_cap=Decimal(100), daily_cap=Decimal(500)),
            autonomy=autonomy,
        )
        return Engine(DEFAULT_WALLET_RULES, policy, InMemorySink())

    def _transfer(self, amount: Decimal, seen: bool = True) -> Intent:
        return Intent(
            actor=Actor.AGENT,
            action=Action.TRANSFER,
            amount=amount,
            currency="USDC",
            artifacts=(Artifact(ArtifactKind.ADDRESS, "0xabc", {"seen_before": seen}),),
        )

    def test_advanced_executes_silently_inside_envelope(self) -> None:
        verdict = self._engine(Autonomy.ADVANCED).evaluate(self._transfer(Decimal(10)))
        self.assertEqual(verdict.decision, Decision.ALLOW)

    def test_normal_asks_even_when_clean(self) -> None:
        verdict = self._engine(Autonomy.NORMAL).evaluate(self._transfer(Decimal(10)))
        self.assertEqual(verdict.decision, Decision.CONFIRM)

    def test_advanced_is_not_unlimited(self) -> None:
        """Продвинутый уровень не пробивает конверт."""
        verdict = self._engine(Autonomy.ADVANCED).evaluate(self._transfer(Decimal(999)))
        self.assertEqual(verdict.decision, Decision.CONFIRM)
        self.assertTrue(any("лимит" in r for r in verdict.reasons))

    def test_daily_cap_counts_prior_spend(self) -> None:
        engine = self._engine(Autonomy.ADVANCED)
        verdict = engine.evaluate(self._transfer(Decimal(90)), spent_today=Decimal(450))
        self.assertEqual(verdict.decision, Decision.CONFIRM)


if __name__ == "__main__":
    unittest.main(verbosity=2)
