/**
 * Результат оценки.
 *
 * Язык вероятностей, а не вердиктов: движок никогда не утверждает
 * "безопасно". Максимум — "сигналов риска не найдено".
 */

export const Decision = Object.freeze({
  ALLOW: 'allow',
  CONFIRM: 'confirm',
  BLOCK: 'block',
});

export const NO_SIGNALS_TEXT =
  'Явных сигналов риска не найдено. Это не гарантия безопасности — ' +
  'проверка видит только известные признаки.';

/**
 * Одно наблюдение. Не приговор — вклад в общую картину.
 * @param {{code: string, severity: number, explanation: string, source?: string}} spec
 */
export function signal(spec) {
  if (!(spec.severity >= 0 && spec.severity <= 1)) {
    throw new RangeError(`severity вне диапазона 0..1: ${spec.severity}`);
  }
  return Object.freeze({
    code: spec.code,
    severity: spec.severity,
    explanation: spec.explanation,
    source: spec.source ?? 'rule',
  });
}

/**
 * Вероятностное объединение: 1 - Π(1 - severity).
 * Много слабых сигналов накапливаются, но score никогда не достигает 1.0.
 */
export function combine(signals) {
  let acc = 1;
  for (const s of signals) acc *= 1 - s.severity;
  return 1 - acc;
}

export function sortedSignals(signals) {
  return [...signals].sort((a, b) => b.severity - a.severity);
}

export function explain(verdict) {
  if (verdict.signals.length === 0) return NO_SIGNALS_TEXT;
  return sortedSignals(verdict.signals).map((s) => `• ${s.explanation}`).join('\n');
}
