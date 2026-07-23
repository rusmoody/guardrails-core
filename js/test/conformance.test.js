/**
 * Реализация на JS против того же общего набора кейсов.
 * Питон гоняет tests/test_conformance.py по этому же файлу.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  artifact, intent, envelope, policy,
  DEFAULT_GUARDIAN_RULES, DEFAULT_WALLET_RULES, Engine, InMemorySink,
} from '../src/index.js';

const here = dirname(fileURLToPath(import.meta.url));
const suite = JSON.parse(
  readFileSync(join(here, '..', '..', 'conformance', 'cases.json'), 'utf8'),
);

const RULE_SETS = { guardian: DEFAULT_GUARDIAN_RULES, wallet: DEFAULT_WALLET_RULES };

function buildPolicy(spec) {
  const e = spec.envelope ?? {};
  return policy({
    envelope: envelope({
      perTxCap: e.perTxCap ?? null,
      dailyCap: e.dailyCap ?? null,
      allowedActions: e.allowedActions ?? null,
      allowlist: e.allowlist ?? [],
      denylist: e.denylist ?? [],
    }),
    autonomy: spec.autonomy ?? 'normal',
  });
}

function buildIntent(spec) {
  return intent({
    actor: spec.actor,
    action: spec.action,
    artifacts: (spec.artifacts ?? []).map((a) => artifact(a.kind, a.value, a.facts ?? {})),
    amount: spec.amount ?? null,
    currency: spec.currency ?? null,
    context: spec.context ?? {},
  });
}

for (const c of suite.cases) {
  test(c.id, () => {
    const engine = new Engine(RULE_SETS[c.rules], buildPolicy(c.policy), new InMemorySink());
    const verdict = engine.evaluate(buildIntent(c.intent), c.spentToday ?? 0);
    const expect = c.expect;

    assert.equal(verdict.decision, expect.decision, c.description);

    if ('score' in expect) {
      assert.ok(
        Math.abs(verdict.score - expect.score) <= suite.tolerance,
        `score ${verdict.score} != ${expect.score}`,
      );
    }
    if ('scoreBelow' in expect) assert.ok(verdict.score < expect.scoreBelow);
    if ('scoreAbove' in expect) assert.ok(verdict.score > expect.scoreAbove);

    const codes = verdict.signals.map((s) => s.code).sort();
    assert.deepEqual(codes, [...expect.signalCodes].sort());
  });
}
