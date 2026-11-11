import { HttpErrorResponse } from '@angular/common/http';

// Nomes amigáveis para os campos que a API costuma devolver nos erros de validação.
const FIELD_LABELS: Record<string, string> = {
  cliente: 'Cliente',
  consumos: 'Consumos',
  data_validade: 'Validade',
  destino: 'Destino',
  estoque: 'Estoque',
  itens: 'Itens',
  nome: 'Nome',
  pedido: 'Pedido',
  preco_unitario: 'Preço unitário',
  preco_venda: 'Preço de venda',
  produto_aproveitado: 'Produto reaproveitado',
  quantidade: 'Quantidade',
  quantidade_peso: 'Peso',
  receitas: 'Receitas',
  status: 'Status',
  subtipo: 'Modalidade',
  tipo: 'Tipo',
  valor_sinal: 'Sinal',
  valor_total: 'Valor total',
};

// Achata o corpo de erro do DRF ({campo: [mensagens]}) em frases legíveis.
function flatten(value: unknown, field?: string): string[] {
  if (value === null || value === undefined) {
    return [];
  }
  if (typeof value === 'string') {
    const label =
      field && field !== 'detail' && field !== 'non_field_errors' ? FIELD_LABELS[field] : null;
    return [label ? `${label}: ${value}` : value];
  }
  if (Array.isArray(value)) {
    return value.flatMap((entry) => flatten(entry, field));
  }
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>).flatMap(([key, entry]) =>
      // Erros por item vêm como lista de objetos; mantém o nome do campo externo.
      flatten(entry, /^\d+$/.test(key) ? field : key),
    );
  }
  return [String(value)];
}

// Converte qualquer erro de requisição em uma mensagem curta para a tela.
export function apiErrorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 0) {
      return 'Não foi possível conectar ao servidor. Verifique a conexão.';
    }
    const body = error.error;
    if (typeof body === 'string' && body.trimStart().startsWith('<')) {
      return `Erro interno no servidor (HTTP ${error.status}).`;
    }
    const messages = [...new Set(flatten(body))];
    if (messages.length > 0) {
      return messages.join(' ');
    }
    return `Erro ${error.status} ao consultar a API.`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return typeof error === 'string' ? error : 'Erro desconhecido ao consultar a API.';
}
