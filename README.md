# guardrails-core

**A decision layer for actions that move money — whether an AI agent proposes them, or a stranger does.**

Zero dependencies. Two implementations — Python and JavaScript — held together by a
shared conformance suite. Auditable by design.

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
scope by design — not by configuration. There is no `identity` artifact kind to enable.

**Hard limits beat autonomy.** The spending envelope always applies. An "advanced"
autonomy level means *"don't ask me about small things within what I allowed"* — it never
means unlimited. Autonomy governs agent-proposed actions only; it never gates inbound
screening.

**Everything is logged.** Every evaluation produces an audit record: what was proposed,
which rules fired, what was decided, and why. For the user this is trust. For the operator
it is evidence.

---

## Architecture

```
adapter → Intent → [ envelope → rules → score → thresholds → autonomy ] → Verdict → audit
```

The engine knows nothing about blockchains, browsers, or messengers. Adapters translate
their world into an `Intent` and act on the `Verdict`.

| Adapter | Actor | Enforcement |
|---|---|---|
| Scam guardian | `COUNTERPARTY` | "Don't send this — here's why" |
| Agent wallet | `AGENT` | "I won't sign this transaction" |

Rules never make network calls. External facts — domain age, report counts, address
history, on-chain reputation — are attached to `Artifact.facts` by the adapter. This keeps
the core dependency-free, fully testable, and identical across languages.

---

## Two implementations, one contract

| | Python | JavaScript |
|---|---|---|
| Path | `guardrails/` | `js/src/` |
| Runtime | 3.10+ | Node 18+, or any modern browser |
| Dependencies | none | none |
| Build step | none | none |
| Use | servers, bots, agents | browsers, extensions, edge |

The JavaScript port exists so that analysis can run **on the user's device**. For a tool
that inspects potentially private messages, not transmitting them at all is a stronger
privacy guarantee than any policy promise.

Two implementations are a real maintenance cost. `conformance/cases.json` is how that cost
is paid: a single set of cases, run by both. A divergence fails a test rather than
surprising a user.

```bash
python -m unittest discover -s tests -v     # 25 tests
cd js && node --test test/*.test.js         # 16 conformance cases
```

Amounts in the conformance suite are integers on purpose — Python's `Decimal` and
JavaScript's `Number` agree exactly only there. Adapters handling fractional amounts should
keep the rounding decision on their side of the boundary.

---

## Performance

Measured on one core, message of ~850 characters with a link and a wallet address:

| | per check | throughput |
|---|---|---|
| JavaScript (Node 22) | 0.013 ms | ~24,000 /sec |
| Python 3.13 | 0.36 ms | ~2,200 /sec |

Pattern matching is the entire cost, and it is small. Run in the browser, concurrency stops
being a server-side question at all: a thousand simultaneous users are a thousand devices
each doing 0.013 ms of work.

---

## Usage

Python:

```python
from guardrails import (
    Action, Actor, Artifact, ArtifactKind, DEFAULT_GUARDIAN_RULES, Engine, Intent,
)

engine = Engine(DEFAULT_GUARDIAN_RULES)

verdict = engine.evaluate(Intent(
    actor=Actor.COUNTERPARTY,
    action=Action.INBOUND_MESSAGE,
    artifacts=(
        Artifact(ArtifactKind.TEXT, "Urgent — confirm the code from the SMS"),
        Artifact(ArtifactKind.DOMAIN, "bank-secure.top", {"domain_age_days": 2}),
    ),
))
print(verdict.decision)     # Decision.BLOCK
print(verdict.explanation)  # ready to show the user
```

JavaScript:

```js
import {
  artifact, intent, DEFAULT_GUARDIAN_RULES, Engine, explain,
} from './js/src/index.js';

const engine = new Engine(DEFAULT_GUARDIAN_RULES);

const verdict = engine.evaluate(intent({
  actor: 'counterparty',
  action: 'inbound_message',
  artifacts: [
    artifact('text', 'Urgent — confirm the code from the SMS'),
    artifact('domain', 'bank-secure.top', { domain_age_days: 2 }),
  ],
}));
console.log(verdict.decision);   // 'block'
console.log(explain(verdict));
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

A rule returns observations, never decisions. The engine combines them. Add the same rule
to both implementations and cover it in `conformance/cases.json`.

---

## Status

Early. The interfaces are settled and the two implementations agree. The rule library is
deliberately small so the shape stays legible.

Built on top of this engine:
[scam-guardian](https://github.com/rusmoody/scam-guardian) — forward a suspicious message,
get an explanation of what's wrong with it.

## License

Apache-2.0
