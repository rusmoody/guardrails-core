/**
 * Два независимых слоя.
 *
 * Envelope  — сколько вообще можно. Жёсткие правила, действуют всегда.
 * Autonomy  — спрашивать ли подтверждение ВНУТРИ конверта.
 */

export const Autonomy = Object.freeze({
  NORMAL: 'normal',
  ADVANCED: 'advanced',
});

/**
 * @param {{
 *   perTxCap?: number|null, dailyCap?: number|null,
 *   allowedActions?: ReadonlyArray<string>|null,
 *   allowlist?: ReadonlyArray<string>, denylist?: ReadonlyArray<string>,
 * }} [spec]
 */
export function envelope(spec = {}) {
  return Object.freeze({
    perTxCap: spec.perTxCap ?? null,
    dailyCap: spec.dailyCap ?? null,
    allowedActions: spec.allowedActions ? new Set(spec.allowedActions) : null,
    allowlist: new Set(spec.allowlist ?? []),
    denylist: new Set(spec.denylist ?? []),
  });
}

/** Что из конверта нарушено. Пустой массив = внутри конверта. */
export function violations(env, intentObj, spentToday = 0) {
  const out = [];

  if (env.allowedActions !== null && !env.allowedActions.has(intentObj.action)) {
    out.push(`действие ${intentObj.action} не разрешено политикой`);
  }

  for (const a of intentObj.artifacts) {
    if (env.denylist.has(a.value)) out.push(`${a.value} в чёрном списке`);
  }

  if (intentObj.amount !== null && intentObj.amount !== undefined) {
    if (env.perTxCap !== null && intentObj.amount > env.perTxCap) {
      out.push(`сумма ${intentObj.amount} выше лимита на операцию ${env.perTxCap}`);
    }
    if (env.dailyCap !== null && spentToday + intentObj.amount > env.dailyCap) {
      out.push(`дневной лимит ${env.dailyCap} будет превышен`);
    }
  }

  return out;
}

/**
 * @param {{envelope?: object, autonomy?: string,
 *          confirmThreshold?: number, blockThreshold?: number}} [spec]
 */
export function policy(spec = {}) {
  return Object.freeze({
    envelope: spec.envelope ?? envelope(),
    autonomy: spec.autonomy ?? Autonomy.NORMAL,
    confirmThreshold: spec.confirmThreshold ?? 0.35,
    blockThreshold: spec.blockThreshold ?? 0.75,
  });
}
