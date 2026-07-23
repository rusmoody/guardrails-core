# guardrails-core

**A decision layer for actions that move money — whether an AI agent proposes them, or a stranger does.**

Zero dependencies. Pure Python. Auditable by design.

---

## The problem

Two things are happening at once.

AI agents are starting to act on our behalf: holding funds, paying for services, executing
transactions without a human in the loop for every step. And AI-powered scams are getting
better at convincing people to move money themselves.

These look like opposite problems. Structurally they are the same one: **an action is
proposed, and something has to decide whether it should happen.**

`guardrails-core` is that something. One engine, pointed in two directions.

---

## Design principles

**The model proposes, the code decides.** An LLM never signs a transaction. It emits a
structured `Intent`; deterministic code evaluates it. Free-form model output never
triggers execution.

**Probabilities, not verdicts.** The engine never says "safe". Signals combine as
`1 - Π(1 - severity)`, so the score approaches but never reaches 1.0. Absence of signals
is reported as absence of signals — not as a guarantee.

**Artifacts, not identities.** We evaluate what participates in the scheme: addresses,
contracts, domains, links, message structure. We do not profile the person on the other
side. Knowing *who* is running a scam does not stop the transfer; recognising the *pattern*
does. Deanonymisation adds near-zero protective value and maximal risk, so it is out of
scope by design — not by configuration.

**Hard limits beat autonomy.** The spending envelope always applies. An "advanced"
autonomy level means *"don't ask me about small things within what I allowed"* — it never
means unlimited.

**Everything is logged.** Every evaluation produces an audit record: what was proposed,
which rules fired, what was decided, and why. For the user this is trust. For the operator
it is evidence.

---

## Architecture

```
adapter → Intent → [ envelope → rules → score → thresholds → autonomy ] → Verdict → audit
```

The engine knows nothing about blockchains or messengers. Adapters translate their world
into an `Intent` and act on the `Verdict`.

| Adapter | Actor | Enforcement |
|---|---|---|
| Scam guardian | `COUNTERPARTY` | "Don't send this — here's why" |
| Agent wallet | `AGENT` | "I won't sign this transaction" |

Rules never make network calls. External facts (domain age, report counts, address
history) are attached to `Artifact.facts` by the adapter, which keeps the core
dependency-free and fully testable.

---

## Usage

```python
from decimal import Decimal
from guardrails import (
    Action, Actor, Artifact, ArtifactKind, Autonomy,
    DEFAULT_GUARDIAN_RULES, Engine, Envelope, Intent, Policy,
)

engine = Engine(DEFAULT_GUARDIAN_RULES)

intent = Intent(
    actor=Actor.COUNTERPARTY,
    action=Action.INBOUND_MESSAGE,
    artifacts=(
        Artifact(ArtifactKind.TEXT, "Срочно! Служба безопасности: подтвердите код"),
        Artifact(ArtifactKind.DOMAIN, "bank-secure.top", {"domain_age_days": 2}),
    ),
)

verdict = engine.evaluate(intent)
print(verdict.decision)     # Decision.BLOCK
print(verdict.explanation)  # human-readable, ready to show the user
```

Agent wallet, with a spending envelope:

```python
policy = Policy(
    envelope=Envelope(per_tx_cap=Decimal(100), daily_cap=Decimal(500)),
    autonomy=Autonomy.ADVANCED,
)
engine = Engine(DEFAULT_WALLET_RULES, policy)
verdict = engine.evaluate(transfer_intent, spent_today=Decimal(450))
```

---

## Writing a rule

```python
class MyRule:
    code = "my_rule"

    def applies_to(self, intent) -> bool:
        return intent.action is Action.TRANSFER

    def evaluate(self, intent) -> list[Signal]:
        return [Signal(code=self.code, severity=0.4, explanation="...")]
```

A rule returns observations, never decisions. The engine combines them.

---

## Status

Early. The interfaces are settled; the rule library is deliberately small so the shape
stays legible. Contributions of scam patterns — especially in under-served languages —
are the most valuable thing anyone can add.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## License

Apache-2.0
