import { OrderItem } from '../models/api.model';
import { orderCategory } from './order-category';

const item = (nome: string): OrderItem => ({
  produto: 1,
  receita: null,
  quantidade: 1,
  preco_unitario: '1.00',
  produto_nome: nome,
});

describe('orderCategory', () => {
  it('reconhece bolos, doces e kits pelo nome dos itens', () => {
    expect(orderCategory([item('Bolo 1kg massa branca')])).toBe('bolo');
    expect(orderCategory([item('Brigadeiro tradicional')])).toBe('doce');
    expect(orderCategory([item('Kit festa 20 pessoas')])).toBe('kit');
  });

  it('prioriza kit, depois bolo, e devolve null sem correspondência', () => {
    expect(orderCategory([item('Brigadeiro'), item('Bolo de cenoura')])).toBe('bolo');
    expect(orderCategory([item('Refrigerante')])).toBeNull();
  });
});
