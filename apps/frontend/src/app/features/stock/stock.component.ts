import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  LucideChevronDown,
  LucideDynamicIcon,
  LucidePlus,
  LucideSearch,
  LucidePackage,
  LucideRefreshCw,
  provideLucideIcons,
} from '@lucide/angular';
import { MetricCardsComponent } from '../../shared/components/metric-cards/metric-cards.component';
import { MetricCardItem } from '../../shared/components/metric-cards/metric-cards.model';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';
import { StockProductCardComponent } from './components/stock-product-card/stock-product-card.component';
import { StockProductCardItem } from './components/stock-product-card/stock-product-card.model';

type StockCategory = 'bolos' | 'doces' | 'sobremesas';

interface StockItem extends StockProductCardItem {
  category: StockCategory;
}

@Component({
  selector: 'app-stock',
  standalone: true,
  imports: [
    CommonModule,
    LucideDynamicIcon,
    PageGreetingComponent,
    MetricCardsComponent,
    StockProductCardComponent,
  ],
  providers: [
    provideLucideIcons(LucideChevronDown, LucidePackage, LucidePlus, LucideRefreshCw, LucideSearch),
  ],
  templateUrl: './stock.component.html',
  styleUrls: ['./stock.component.scss'],
})
export class StockComponent {
  readonly greetingActions: PageAction[] = [
    { label: 'Atualizar Estoque', icon: 'refresh-cw', variant: 'secondary' },
    { label: 'Nova Produção (Pedidos)', route: '/pedidos', icon: 'plus', variant: 'primary' },
  ];

  readonly summaryCards: MetricCardItem[] = [
    {
      label: 'Produtos armazenados',
      value: '41 itens',
      subtext: '4 categorias ativas',
      icon: 'package',
      variant: 'destaque',
    },
    {
      label: 'Custo total em estoque',
      value: 'R$ 8.940',
      subtext: 'Atualizado hoje, 09:30',
      icon: 'banknote',
      variant: 'neutro',
    },
    {
      label: 'Alertas de validade',
      value: '4 lotes',
      subtext: '1 crítico • 1 atenção • 2 preventivos',
      icon: 'calendar',
      variant: 'alerta',
    },
  ];

  readonly selectedCategory = signal<'todos' | StockCategory>('todos');
  readonly searchTerm = signal('');

  readonly stockItems = signal<StockItem[]>([
    {
      id: 'ART-0104',
      name: 'Bolo Trufado de Chocolate Belga',
      category: 'bolos',
      categoryLabel: 'Bolos artesanais',
      description: 'Massa chiffon de cacau 100%, recheio cremoso de brigadeiro belga.',
      quantity: 8,
      unit: 'unidades',
      basePrice: 'R$ 95,00',
      priceUnit: 'kg',
      margin: '71.4%',
      sizes: [
        { label: 'P', value: '1,5 kg' },
        { label: 'M', value: '2,5 kg' },
        { label: 'G', value: '3,5 kg' },
      ],
      expiry: 'Hoje (15/09/2026)',
      expiryDetail: 'Vence hoje',
      status: 'critico',
      statusLabel: 'Crítico',
      image: '/images/auth-cake.jpg',
    },
    {
      id: 'ART-0129',
      name: 'Red Velvet com Frutas Vermelhas',
      category: 'bolos',
      categoryLabel: 'Bolos artesanais',
      description: 'Pão de ló aveludado com recheio de frutas vermelhas e cream cheese.',
      quantity: 12,
      unit: 'unidades',
      basePrice: 'R$ 105,00',
      priceUnit: 'kg',
      margin: '68.2%',
      sizes: [
        { label: 'P', value: '1,5 kg' },
        { label: 'M', value: '2,5 kg' },
        { label: 'G', value: '3,5 kg' },
      ],
      expiry: '20/09/2026',
      expiryDetail: 'Vence em 5 dias',
      status: 'atencao',
      statusLabel: 'Atenção',
      image: '/images/auth-cake.jpg',
    },
    {
      id: 'ART-0131',
      name: 'Delícia de Morango & Ninho',
      category: 'sobremesas',
      categoryLabel: 'Sobremesas especiais',
      description: 'Massa amanteigada de baunilha, chantilly leve e morangos frescos.',
      quantity: 6,
      unit: 'unidades',
      basePrice: 'R$ 88,00',
      priceUnit: 'kg',
      margin: '64.8%',
      sizes: [
        { label: 'P', value: '1,2 kg' },
        { label: 'M', value: '2 kg' },
      ],
      expiry: '26/09/2026',
      expiryDetail: 'Vence em 11 dias',
      status: 'preventivo',
      statusLabel: 'Preventivo',
      image: '/images/auth-cake.jpg',
    },
    {
      id: 'DOC-0015',
      name: 'Coleção Brigadeiros Nobres',
      category: 'doces',
      categoryLabel: 'Doces & brigadeiros',
      description: 'Caixa luxo com 25 unidades sortidas, pronta para presente.',
      quantity: 15,
      unit: 'caixas',
      basePrice: 'R$ 28,50',
      priceUnit: 'caixa',
      margin: '59.6%',
      sizes: [
        { label: '25', value: 'un.' },
        { label: '50', value: 'un.' },
      ],
      expiry: '29/09/2026',
      expiryDetail: 'Vence em 14 dias',
      status: 'preventivo',
      statusLabel: 'Preventivo',
      image: '/images/auth-cake.jpg',
    },
  ]);

  readonly filteredItems = computed(() => {
    const term = this.searchTerm().trim().toLowerCase();
    const category = this.selectedCategory();

    return this.stockItems().filter((item) => {
      const matchesTerm =
        !term ||
        item.name.toLowerCase().includes(term) ||
        item.id.toLowerCase().includes(term) ||
        item.categoryLabel.toLowerCase().includes(term);
      return matchesTerm && (category === 'todos' || item.category === category);
    });
  });

  setCategory(category: 'todos' | StockCategory): void {
    this.selectedCategory.set(category);
  }
}
