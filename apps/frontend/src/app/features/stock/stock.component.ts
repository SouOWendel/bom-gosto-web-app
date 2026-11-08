import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
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
import { StockLot } from '../../core/models/api.model';
import { DomainApiService } from '../../core/services/domain-api.service';

type StockCategory = 'bolos' | 'doces' | 'sobremesas' | 'outros';

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
export class StockComponent implements OnInit {
  private readonly domainApi = inject(DomainApiService);
  private readonly router = inject(Router);
  readonly stockLots = signal<StockLot[]>([]);

  readonly loadError = signal<string | null>(null);

  readonly greetingActions: PageAction[] = [
    { label: 'Atualizar Estoque', icon: 'refresh-cw', variant: 'secondary' },
    { label: 'Nova Produção (Pedidos)', route: '/pedidos', icon: 'plus', variant: 'primary' },
  ];

  get summaryCards(): MetricCardItem[] {
    const lots = this.stockLots();
    const critical = lots.filter(
      (lot) => lot.vencido || lot.alerta_validade?.nivel === 'critico',
    ).length;
    const attention = lots.filter((lot) => lot.alerta_validade?.nivel === 'atencao').length;
    const preventive = lots.filter((lot) => lot.alerta_validade?.nivel === 'preventivo').length;
    const totalCost = lots.reduce((total, lot) => total + this.toNumber(lot.custo), 0);

    return [
      {
        label: 'Produtos armazenados',
        value: `${lots.length} lotes`,
        subtext: 'Lotes retornados pela API',
        icon: 'package',
        variant: 'destaque',
      },
      {
        label: 'Custo total em estoque',
        value: this.formatCurrency(totalCost),
        subtext: 'Soma do custo informado por lote',
        icon: 'banknote',
        variant: 'neutro',
      },
      {
        label: 'Alertas de validade',
        value: `${critical + attention + preventive} lotes`,
        subtext: `${critical} críticos • ${attention} atenção • ${preventive} preventivos`,
        icon: 'calendar',
        variant: 'alerta',
      },
    ];
  }

  readonly selectedCategory = signal<'todos' | StockCategory>('todos');
  readonly searchTerm = signal('');
  readonly currentPage = signal(1);
  readonly pageSize = 6;

  readonly stockItems = computed<StockItem[]>(() =>
    this.stockLots().map((lot) => this.toStockItem(lot)),
  );

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
  readonly paginatedItems = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize;
    return this.filteredItems().slice(start, start + this.pageSize);
  });
  readonly totalPages = computed(() => Math.ceil(this.filteredItems().length / this.pageSize));
  readonly pageNumbers = computed(() =>
    Array.from({ length: this.totalPages() }, (_, index) => index + 1),
  );
  readonly visibleRange = computed(() => {
    const total = this.filteredItems().length;
    if (total === 0) {
      return { start: 0, end: 0 };
    }
    return {
      start: (this.currentPage() - 1) * this.pageSize + 1,
      end: Math.min(this.currentPage() * this.pageSize, total),
    };
  });

  setCategory(category: 'todos' | StockCategory): void {
    this.selectedCategory.set(category);
    this.currentPage.set(1);
  }

  onSearch(value: string): void {
    this.searchTerm.set(value);
    this.currentPage.set(1);
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
    }
  }

  ngOnInit(): void {
    this.domainApi.getStock().subscribe({
      next: (lots) => {
        this.stockLots.set(lots);
        this.loadError.set(null);
        this.currentPage.set(1);
      },
      error: (error: unknown) => {
        const detail = this.errorDetail(error);
        this.loadError.set(detail);
        console.error('Falha ao carregar os lotes de estoque.', error);
      },
    });
  }

  onTechnicalSheet(): void {
    void this.router.navigate(['/receitas']);
  }

  onViewProduct(): void {
    void this.router.navigate(['/produtos']);
  }

  private toStockItem(lot: StockLot): StockItem {
    const alertLevel = lot.alerta_validade?.nivel;
    const isCritical = lot.vencido || alertLevel === 'critico';
    const status = isCritical ? 'critico' : alertLevel === 'atencao' ? 'atencao' : 'preventivo';
    const productName = lot.produto_nome || `Produto #${lot.id_produto}`;

    return {
      id: String(lot.id_estoque),
      name: productName,
      category: 'outros',
      categoryLabel: lot.produto_nome ? 'Produto em Estoque' : 'Categoria não informada',
      description: `Lote #${lot.id_estoque} • ${productName}`,
      quantity: this.toNumber(lot.quantidade_disponivel),
      unit: 'un.',
      basePrice: lot.produto_preco_venda
        ? this.formatCurrency(Number(lot.produto_preco_venda))
        : this.formatCurrencyOrUnavailable(lot.custo),
      priceUnit: 'un.',
      margin: 'Produção',
      sizes: [],
      expiry: this.formatDate(lot.data_validade),
      expiryDetail: this.expiryDetail(lot),
      status,
      statusLabel: isCritical
        ? 'Crítico'
        : alertLevel === 'atencao'
          ? 'Atenção'
          : alertLevel === 'preventivo'
            ? 'Preventivo'
            : 'Sem alerta',
      image: '/images/auth-cake.jpg',
    };
  }

  private toNumber(value: string | null): number {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  private formatCurrency(value: number): string {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  private formatCurrencyOrUnavailable(value: string | null): string {
    return value === null ? 'Não informado' : this.formatCurrency(this.toNumber(value));
  }

  private formatDate(value: string | null): string {
    if (value === null) {
      return 'Não informada';
    }

    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('pt-BR');
  }

  private expiryDetail(lot: StockLot): string {
    const alert = lot.alerta_validade;
    if (lot.vencido && alert === null) {
      return 'Vencido';
    }
    if (alert === null) {
      return lot.data_validade === null ? 'Sem validade informada' : 'Sem alerta';
    }
    if (alert.dias_para_vencer < 0) {
      return `Vencido há ${Math.abs(alert.dias_para_vencer)} dia(s)`;
    }
    if (alert.dias_para_vencer === 0) {
      return 'Vence hoje';
    }
    return `Vence em ${alert.dias_para_vencer} dia(s)`;
  }

  private errorDetail(error: unknown): string {
    return error instanceof Error ? error.message : 'Erro desconhecido ao consultar a API.';
  }
}
