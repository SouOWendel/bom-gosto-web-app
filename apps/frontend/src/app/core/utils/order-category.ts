import { OrderItem } from '../models/api.model';

export type OrderCategory = 'bolo' | 'doce' | 'kit';

// Palavras que indicam a categoria pelo nome do produto ou da receita do item.
const KEYWORDS: Array<[OrderCategory, string[]]> = [
  ['kit', ['kit', 'festa', 'combo']],
  ['bolo', ['bolo', 'torta', 'caseirinho', 'vulcão', 'vulcao']],
  ['doce', ['brigadeiro', 'beijinho', 'doce', 'docinho', 'trufa', 'pote', 'banoffee', 'bombom']],
];

// Nome que aparece para o item: produto pronto ou receita.
export function orderItemName(item: OrderItem): string {
  return item.produto_nome ?? item.receita_nome ?? '';
}

// Categoria do pedido pela ordem de prioridade kit > bolo > doce; null se nada casar.
export function orderCategory(items: OrderItem[]): OrderCategory | null {
  const names = items.map((item) => orderItemName(item).toLocaleLowerCase('pt-BR'));
  for (const [category, words] of KEYWORDS) {
    if (names.some((name) => words.some((word) => name.includes(word)))) {
      return category;
    }
  }
  return null;
}
