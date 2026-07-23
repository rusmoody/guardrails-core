/**
 * Правила.
 *
 * Правило смотрит на Intent и возвращает сигналы. Оно НЕ принимает решений.
 * Правило не ходит в сеть: всё внешнее приезжает в artifact.facts.
 */

import { Action, Actor, ArtifactKind, artifactsOf } from './intent.js';
import { signal } from './verdict.js';

/** Свежезарегистрированный домен — классика фишинга. */
export class FreshDomainRule {
  constructor(daysThreshold = 30) {
    this.code = 'fresh_domain';
    this.daysThreshold = daysThreshold;
  }

  appliesTo(intentObj) {
    return artifactsOf(intentObj, ArtifactKind.DOMAIN).length > 0
      || artifactsOf(intentObj, ArtifactKind.URL).length > 0;
  }

  evaluate(intentObj) {
    const out = [];
    for (const a of intentObj.artifacts) {
      const age = a.facts.domain_age_days;
      if (age === undefined || age === null || age >= this.daysThreshold) continue;
      out.push(signal({
        code: this.code,
        severity: age < 7 ? 0.6 : 0.4,
        explanation: `Домен ${a.value} зарегистрирован ${age} дн. назад. `
          + 'Мошеннические сайты обычно живут считаные дни.',
      }));
    }
    return out;
  }
}

/** Артефакт встречается в публичных реестрах жалоб. */
export class ScamReportsRule {
  constructor() {
    this.code = 'scam_reports';
  }

  appliesTo(intentObj) {
    return intentObj.artifacts.length > 0;
  }

  evaluate(intentObj) {
    const out = [];
    for (const a of intentObj.artifacts) {
      const reports = a.facts.scam_reports;
      if (!reports) continue;
      out.push(signal({
        code: this.code,
        severity: Math.min(0.9, 0.3 + 0.1 * reports),
        explanation: `${a.value} упоминается в ${reports} сообщениях о мошенничестве.`,
      }));
    }
    return out;
  }
}

/** Давление и срочность — ядро почти любой схемы. */
export class PressurePatternRule {
  constructor() {
    this.code = 'pressure_pattern';
    this.markers = [
      'срочно', 'немедленно', 'никому неговори', 'никому не сообщайте',
      'счёт заблокирован', 'служба безопасности', 'подтвердите код',
      'переведите на безопасный счёт',
    ];
  }

  appliesTo(intentObj) {
    return intentObj.action === Action.INBOUND_MESSAGE
      || intentObj.action === Action.INBOUND_CALL;
  }

  evaluate(intentObj) {
    const hits = [];
    for (const a of artifactsOf(intentObj, ArtifactKind.TEXT)) {
      const lowered = a.value.toLowerCase();
      for (const m of this.markers) if (lowered.includes(m)) hits.push(m);
    }
    if (hits.length === 0) return [];
    const unique = [...new Set(hits)].sort();
    return [signal({
      code: this.code,
      severity: Math.min(0.85, 0.3 + 0.2 * hits.length),
      explanation: 'В сообщении есть признаки давления: ' + unique.join(', ')
        + '. Настоящие организации не торопят и не просят коды.',
    })];
  }
}

/** Требование необратимого платежа. */
export class IrreversibleChannelRule {
  constructor() {
    this.code = 'irreversible_channel';
  }

  appliesTo(intentObj) {
    return intentObj.actor === Actor.COUNTERPARTY;
  }

  evaluate(intentObj) {
    const channel = intentObj.context.payment_channel;
    if (!['gift_card', 'crypto', 'wire', 'p2p_transfer'].includes(channel)) return [];
    return [signal({
      code: this.code,
      severity: 0.55,
      explanation: `Просят оплату через необратимый канал (${channel}). `
        + 'Вернуть такой платёж почти невозможно.',
    })];
  }
}

/** Агент отправляет средства на адрес без истории взаимодействия. */
export class UnknownRecipientRule {
  constructor() {
    this.code = 'unknown_recipient';
  }

  appliesTo(intentObj) {
    return intentObj.actor === Actor.AGENT && intentObj.action === Action.TRANSFER;
  }

  evaluate(intentObj) {
    const out = [];
    for (const a of artifactsOf(intentObj, ArtifactKind.ADDRESS)) {
      if (a.facts.seen_before) continue;
      out.push(signal({
        code: this.code,
        severity: 0.4,
        explanation: `Получатель ${a.value} раньше не встречался в истории.`,
      }));
    }
    return out;
  }
}

export const DEFAULT_GUARDIAN_RULES = Object.freeze([
  new FreshDomainRule(),
  new ScamReportsRule(),
  new PressurePatternRule(),
  new IrreversibleChannelRule(),
]);

export const DEFAULT_WALLET_RULES = Object.freeze([
  new ScamReportsRule(),
  new UnknownRecipientRule(),
]);
