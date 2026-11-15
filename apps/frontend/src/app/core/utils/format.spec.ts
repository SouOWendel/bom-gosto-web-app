import {
  expiryText,
  formatCurrency,
  formatQuantity,
  parseDecimal,
  toDisplayDecimal,
} from './format';

describe('format', () => {
  it('converte o texto digitado para o decimal da API', () => {
    expect(parseDecimal('1.234,50')).toBe('1234.50');
    expect(parseDecimal('1234,5')).toBe('1234.5');
    expect(parseDecimal('1234.5')).toBe('1234.5');
    expect(parseDecimal(' R$ 10,00 ')).toBe('10.00');
    expect(parseDecimal('')).toBe('');
  });

  it('exibe decimais da API no formato pt-BR', () => {
    expect(toDisplayDecimal('1.50')).toBe('1,5');
    expect(formatQuantity('0.05')).toBe('0,05');
    expect(formatQuantity(null)).toBe('Não informado');
  });

  it('formata moeda e trata valores inválidos', () => {
    expect(formatCurrency(80.9)).toMatch(/R\$\s80,90/);
    expect(formatCurrency(Number.NaN)).toBe('—');
  });

  it('descreve o prazo de validade', () => {
    expect(expiryText(-2)).toBe('Vencido há 2 dia(s)');
    expect(expiryText(0)).toBe('Vence hoje');
    expect(expiryText(5)).toBe('Vence em 5 dia(s)');
  });
});
