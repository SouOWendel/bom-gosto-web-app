import { Order } from '../models/api.model';

/**
 * Diz se o pedido tem cobrança de cliente.
 * Só o pedido externo tem; a reposição interna não tem sinal, saldo nem forma de pagamento.
 */
export function hasPayment(order: Pick<Order, 'tipo'>): boolean {
  return order.tipo === 'externo';
}
