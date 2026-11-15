import { HttpErrorResponse } from '@angular/common/http';
import { apiErrorMessage } from './api-error';

describe('apiErrorMessage', () => {
  it('converte erros de campo do DRF em frases legíveis', () => {
    const error = new HttpErrorResponse({
      status: 400,
      error: { itens: ['Pedidos de vitrine devem referenciar produtos prontos.'] },
    });
    expect(apiErrorMessage(error)).toBe(
      'Itens: Pedidos de vitrine devem referenciar produtos prontos.',
    );
  });

  it('usa o detail sem prefixo e lê erros por item', () => {
    expect(
      apiErrorMessage(new HttpErrorResponse({ status: 400, error: { detail: 'Negado.' } })),
    ).toBe('Negado.');
    const porItem = new HttpErrorResponse({
      status: 400,
      error: { itens: [{ quantidade: ['A quantidade deve ser maior que zero.'] }] },
    });
    expect(apiErrorMessage(porItem)).toBe('Quantidade: A quantidade deve ser maior que zero.');
  });

  it('não mostra HTML de erro do servidor', () => {
    const error = new HttpErrorResponse({ status: 500, error: '<!DOCTYPE html><html></html>' });
    expect(apiErrorMessage(error)).toBe('Erro interno no servidor (HTTP 500).');
  });
});
