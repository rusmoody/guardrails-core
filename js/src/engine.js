/**
 * Движок вердикта.
 *
 * Порядок жёсткий и намеренный:
 *   1. Конверт лимитов.  2. Правила собирают сигналы.  3. Свёртка в score.
 *   4. Пороги.  5. Уровень автономии.  6. Лог.
 *
 * LLM в этой цепочке не участвует. Модель предлагает Intent — и всё.
 */

import { Actor } from './intent.js';
import { policy as makePolicy, violations, Autonomy } from './policy.js';
import { combine, Decision, sortedSignals } from './verdict.js';

export class InMemorySink {
  constructor() {
    this.records = [];
  }

  write(record) {
    this.records.push(record);
  }
}

function auditRecord(intentObj, verdict) {
  return Object.freeze({
    intentId: intentObj.intentId,
    at: new Date().toISOString(),
    actor: intentObj.actor,
    action: intentObj.action,
    artifacts: intentObj.artifacts.map((a) => `${a.kind}:${a.value}`),
    decision: verdict.decision,
    score: Math.round(verdict.score * 1e4) / 1e4,
    signals: sortedSignals(verdict.signals),
    reasons: verdict.reasons,
  });
}

export class Engine {
  constructor(rules, policyObj = null, sink = null) {
    this.rules = [...rules];
    this.policy = policyObj ?? makePolicy();
    this.sink = sink ?? new InMemorySink();
  }

  evaluate(intentObj, spentToday = 0) {
    const reasons = [];

    // 1. Жёсткий слой. Не пробивается ни правилами, ни уровнем автономии.
    const envViolations = violations(this.policy.envelope, intentObj, spentToday);

    // 2-3. Мягкий слой.
    const signals = [];
    for (const rule of this.rules) {
      if (rule.appliesTo(intentObj)) signals.push(...rule.evaluate(intentObj));
    }
    const score = combine(signals);

    // 4. Пороги.
    let decision;
    if (score >= this.policy.blockThreshold) {
      decision = Decision.BLOCK;
      reasons.push(`score ${score.toFixed(2)} выше порога блокировки`);
    } else if (score >= this.policy.confirmThreshold) {
      decision = Decision.CONFIRM;
      reasons.push(`score ${score.toFixed(2)} выше порога подтверждения`);
    } else {
      decision = Decision.ALLOW;
    }

    // 5. Конверт важнее автономии.
    if (envViolations.length > 0) {
      if (decision !== Decision.BLOCK) decision = Decision.CONFIRM;
      reasons.push(...envViolations);
    } else if (
      decision === Decision.ALLOW
      && intentObj.actor === Actor.AGENT
      && this.policy.autonomy === Autonomy.NORMAL
    ) {
      // Уровень автономии касается только действий агента от нашего имени.
      decision = Decision.CONFIRM;
      reasons.push('обычный уровень автономии — подтверждаем вручную');
    }

    const verdict = Object.freeze({
      intentId: intentObj.intentId,
      decision,
      score,
      signals: Object.freeze(signals),
      reasons: Object.freeze(reasons),
    });

    // 6.
    this.sink.write(auditRecord(intentObj, verdict));
    return verdict;
  }
}
