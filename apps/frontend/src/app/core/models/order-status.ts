import { Order } from './api.model';

// Nome de cada status do pedido, usado igual em todas as telas.
export const ORDER_STATUS_LABELS: Record<Order['status'], string> = {
  pedido_feito: 'Pendente',
  em_producao: 'Em produção',
  producao_concluida: 'Pronto',
  concluido: 'Concluído',
  cancelado: 'Cancelado',
};
