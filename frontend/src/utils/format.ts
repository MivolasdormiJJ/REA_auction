const rublesFormatter = new Intl.NumberFormat('ru-RU', {
  style: 'currency',
  currency: 'RUB',
  maximumFractionDigits: 0,
});

/** Переводит сумму в копейках в строку вида «1 500 ₽»; для null возвращает «—». */
export function kopecksToRubles(kopecks: number | null): string {
  if (kopecks == null) return '—';
  return rublesFormatter.format(kopecks / 100);
}
