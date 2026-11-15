export type MetricVariant = 'pedidos' | 'destaque' | 'alerta' | 'neutro';

export interface MetricCardItem {
  id?: string;
  label: string;
  value: string | number;
  subtext?: string;
  icon?: string;
  variant?: MetricVariant;
}
