export type StockProductStatus = 'critico' | 'atencao' | 'preventivo' | 'normal';

// Dados de um lote de produto pronto exibidos no cartão do estoque (RF10).
export interface StockProductCardItem {
  id: string;
  name: string;
  image: string;
  status: StockProductStatus;
  statusLabel: string;
  quantity: number;
  unit: string;
  expiry: string;
  expiryDetail: string;
  salePrice: string;
  lotCost: string;
}
