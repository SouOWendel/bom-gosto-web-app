import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { LucideDynamicIcon, LucidePlus, LucideSearch, provideLucideIcons } from '@lucide/angular';
import { MetricCardsComponent } from '../../shared/components/metric-cards/metric-cards.component';
import { MetricCardItem } from '../../shared/components/metric-cards/metric-cards.model';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';
import { StockProductCardComponent } from './components/stock-product-card/stock-product-card.component';
import { StockProductCardItem } from './components/stock-product-card/stock-product-card.model';
import { TablePaginationComponent } from '../../shared/components/table-pagination/table-pagination.component';
import { StockLot } from '../../core/models/api.model';
import { DomainApiService } from '../../core/services/domain-api.service';

@Component({
  selector: 'app-stock',
  standalone: true,
  imports: [
    LucideDynamicIcon,
    PageGreetingComponent,
    MetricCardsComponent,
    StockProductCardComponent,
    TablePaginationComponent,
  ],
  providers: [provideLucideIcons(LucidePlus, LucideSearch)],
  templateUrl: './stock.component.html',
  styleUrls: ['./stock.component.scss'],
})
export class StockComponent implements OnInit {
  private readonly domainApi = inject(DomainApiService);
  readonly stockLots = signal<StockLot[]>([]);

  readonly loadError = signal<string | null>(null);

  readonly greetingActions: PageAction[] = [
    { label: 'Nova produção (Pedidos)', route: '/pedidos', icon: 'plus', variant: 'primary' },
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

  readonly searchTerm = signal('');
  readonly currentPage = signal(1);
  readonly pageSize = 8;

  readonly stockItems = computed<StockProductCardItem[]>(() =>
    this.stockLots().map((lot) => this.toStockItem(lot)),
  );

  readonly filteredItems = computed(() => {
    const term = this.searchTerm().trim().toLowerCase();
    return this.stockItems().filter(
      (item) => !term || item.name.toLowerCase().includes(term) || item.id.includes(term),
    );
  });
  readonly paginatedItems = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize;
    return this.filteredItems().slice(start, start + this.pageSize);
  });
  readonly totalPages = computed(() => Math.ceil(this.filteredItems().length / this.pageSize));

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
        // Lotes totalmente consumidos não têm o que vender; ficam fora da vitrine.
        this.stockLots.set(lots.filter((lot) => this.toNumber(lot.quantidade_disponivel) > 0));
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

  private toStockItem(lot: StockLot): StockProductCardItem {
    const alertLevel = lot.alerta_validade?.nivel;
    const isCritical = lot.vencido || alertLevel === 'critico';
    const status = isCritical
      ? 'critico'
      : alertLevel === 'atencao'
        ? 'atencao'
        : alertLevel === 'preventivo'
          ? 'preventivo'
          : 'normal';
    const productName = lot.produto_nome || `Produto #${lot.id_produto}`;

    return {
      id: String(lot.id_estoque),
      name: productName,
      quantity: this.toNumber(lot.quantidade_disponivel),
      unit: 'un.',
      salePrice: this.formatCurrencyOrUnavailable(lot.produto_preco_venda ?? null),
      lotCost: this.formatCurrencyOrUnavailable(lot.custo),
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
