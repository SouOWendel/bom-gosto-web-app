export type StockProductStatus = 'critico' | 'atencao' | 'preventivo' | 'normal';

export interface StockProductSize {
  label: string;
  value: string;
}

export interface StockProductCardItem {
  id: string;
  name: string;
  categoryLabel: string;
  description: string;
  image: string;
  status: StockProductStatus;
  statusLabel: string;
  quantity: number;
  unit: string;
  expiry: string;
  expiryDetail: string;
  basePrice: string;
  priceUnit: string;
  margin: string;
  sizes: StockProductSize[];
}
