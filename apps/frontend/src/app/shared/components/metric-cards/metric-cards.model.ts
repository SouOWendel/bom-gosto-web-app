export type MetricVariant = 'vendas' | 'pedidos' | 'destaque' | 'alerta' | 'neutro';

export interface MetricCardItem {
  id?: string;
  label: string;
  value: string | number;
  subtext?: string;
  trend?: {
    value: string;
    direction?: 'up' | 'down';
  };
  icon?: string;
  variant?: MetricVariant;
}
