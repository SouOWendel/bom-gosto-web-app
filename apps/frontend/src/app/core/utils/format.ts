// Formatação compartilhada pelas telas (valores, datas e quantidades em pt-BR).

// A API envia decimais como texto; valores inválidos ou nulos viram 0.
export function toNumber(value: string | number | null | undefined): number {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

export function formatCurrency(value: number): string {
  if (!Number.isFinite(value)) {
    return '—';
  }
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export function formatCurrencyOrUnavailable(value: string | null): string {
  return value === null ? 'Não informado' : formatCurrency(toNumber(value));
}

export function formatQuantity(value: string | number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'Não informado';
  }
  return toNumber(value).toLocaleString('pt-BR', { maximumFractionDigits: 2 });
}

// Data da API (YYYY-MM-DD) no formato dd/mm/aaaa.
export function formatDate(value: string | null): string {
  if (value === null) {
    return 'Não informada';
  }
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('pt-BR');
}

// Texto do semáforo de validade (RN17) a partir dos dias que faltam.
export function expiryText(daysToExpire: number): string {
  if (daysToExpire < 0) {
    return `Vencido há ${Math.abs(daysToExpire)} dia(s)`;
  }
  if (daysToExpire === 0) {
    return 'Vence hoje';
  }
  return `Vence em ${daysToExpire} dia(s)`;
}

// Texto digitado ("1.234,50", "1234,5", "1234.5" ou "R$ 10,00") no decimal da API ("1234.50").
// Sem vírgula, o ponto é tratado como separador decimal.
export function parseDecimal(value: string): string {
  const normalized = value.trim().replace(/[R$\s]/g, '');
  return normalized.includes(',') ? normalized.replace(/\./g, '').replace(',', '.') : normalized;
}

// Decimal da API ("1.50") no formato digitável em pt-BR ("1,5").
export function toDisplayDecimal(value: string): string {
  const number = Number(value);
  return Number.isFinite(number) ? String(number).replace('.', ',') : value;
}
