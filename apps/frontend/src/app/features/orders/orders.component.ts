import { Component, computed, inject, OnInit, signal, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  LucideDynamicIcon,
  LucideBan,
  LucideMessageSquare,
  LucidePencil,
  LucidePrinter,
  LucideSearch,
  provideLucideIcons,
} from '@lucide/angular';
import { MetricCardsComponent } from '../../shared/components/metric-cards/metric-cards.component';
import { MetricCardItem } from '../../shared/components/metric-cards/metric-cards.model';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';
import { CancelProductionModalComponent } from '../../shared/components/cancel-production-modal/cancel-production-modal.component';
import { CompleteProductionModalComponent } from '../../shared/components/complete-production-modal/complete-production-modal.component';
import { OrderCreateModalComponent } from '../../shared/components/order-create-modal/order-create-modal.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import {
  CancelOrderPayload,
  CompleteProductionPayload,
  Order as ApiOrder,
  OrderCreationPayload,
  Product,
  ProductionAnalysis,
  Recipe,
} from '../../core/models/api.model';
import { DomainApiService } from '../../core/services/domain-api.service';
import { TablePaginationComponent } from '../../shared/components/table-pagination/table-pagination.component';

type OrderStatus = 'retirada' | 'producao' | 'pendente' | 'cancelado';
type OrderCategory = 'bolos' | 'doces' | 'kits';

// Ação confirmada pela confeiteira após validar o pedido: produzir ou atender pelo estoque pronto.
interface PendingStart {
  order: OrderRow;
  analysis: ProductionAnalysis;
  mode: 'producao' | 'estoque';
}

interface OrderRow {
  id: string;
  customer: string;
  phone: string;
  address: string;
  item: string;
  reuseName: string;
  category: OrderCategory | null;
  total: string;
  payment: string;
  status: OrderStatus;
  statusLabel: string;
  schedule: string;
  detail: string;
  action: string;
  image: string;
  apiOrder: ApiOrder;
  analysis: ProductionAnalysis | null;
}

@Component({
  selector: 'app-orders',
  standalone: true,
  imports: [
    TablePaginationComponent,
    CommonModule,
    LucideDynamicIcon,
    PageGreetingComponent,
    MetricCardsComponent,
    CancelProductionModalComponent,
    CompleteProductionModalComponent,
    OrderCreateModalComponent,
    ConfirmDialogComponent,
  ],
  providers: [
    provideLucideIcons(LucideBan, LucideMessageSquare, LucidePencil, LucidePrinter, LucideSearch),
  ],
  templateUrl: './orders.component.html',
  styleUrls: ['./orders.component.scss'],
})
export class OrdersComponent implements OnInit {
  private readonly domainApi = inject(DomainApiService);

  readonly isCancelModalOpen = signal(false);
  readonly isCompleteModalOpen = signal(false);
  readonly isCreateModalOpen = signal(false);
  readonly selectedOrder = signal<OrderRow | null>(null);
  readonly loadError = signal<string | null>(null);
  readonly actionError = signal<string | null>(null);
  readonly createError = signal<string | null>(null);
  readonly recipes = signal<Recipe[]>([]);
  readonly isEditModalOpen = signal(false);
  readonly creationInProgress = signal(false);
  readonly operationInProgress = signal(false);
  readonly products = signal<Product[]>([]);
  readonly pendingStart = signal<PendingStart | null>(null);
  readonly currentPage = signal(1);
  readonly pageSize = 6;
  @ViewChild(CancelProductionModalComponent)
  private cancelProductionModal?: CancelProductionModalComponent;
  @ViewChild(CompleteProductionModalComponent)
  private completeProductionModal?: CompleteProductionModalComponent;

  readonly greetingActions: PageAction[] = [
    { label: '+ Novo Pedido', icon: 'plus', variant: 'primary' },
  ];

  readonly orders = signal<OrderRow[]>([]);
  readonly statusCounts = computed(() => {
    const orders = this.orders();
    return {
      todos: orders.length,
      pendente: orders.filter((order) => order.status === 'pendente').length,
      producao: orders.filter((order) => order.status === 'producao').length,
      retirada: orders.filter((order) => order.status === 'retirada').length,
      cancelado: orders.filter((order) => order.status === 'cancelado').length,
    };
  });
  readonly waitingProductionCount = computed(
    () => this.orders().filter((order) => order.apiOrder.status === 'pedido_feito').length,
  );
  readonly ordersSubtitle = computed(
    () =>
      `${this.orders().length} pedidos cadastrados • ${this.waitingProductionCount()} aguardando produção`,
  );

  get summaryCards(): MetricCardItem[] {
    const orders = this.orders();
    const inProduction = orders.filter((order) => order.status === 'producao');
    const ready = orders.filter(
      (order) =>
        order.apiOrder.status === 'producao_concluida' && order.apiOrder.tipo === 'externo',
    ).length;
    const pendingBalance = orders
      .filter((order) => order.status !== 'cancelado' && order.status !== 'retirada')
      .reduce(
        (total, order) =>
          total +
          Math.max(
            0,
            this.toNumber(order.apiOrder.valor_total) - this.toNumber(order.apiOrder.valor_sinal),
          ),
        0,
      );
    const productionValue = inProduction.reduce(
      (total, order) => total + this.toNumber(order.apiOrder.valor_total),
      0,
    );

    return [
      {
        label: 'Em produção',
        value: this.formatCurrency(productionValue),
        subtext: `${inProduction.length} pedidos em produção`,
        icon: 'calendar',
        variant: 'destaque',
      },
      {
        label: 'Prontos p/ retirada',
        value: `${ready} encomendas`,
        subtext: 'Pedidos externos prontos para consumo',
        icon: 'package',
        variant: 'alerta',
      },
      {
        label: 'Pagamentos pendentes',
        value: this.formatCurrency(pendingBalance),
        subtext: 'Saldo calculado pelo sinal informado',
        icon: 'banknote',
        variant: 'pedidos',
      },
      {
        label: 'Pedidos ativos',
        value: String(
          orders.filter((order) => order.status !== 'cancelado' && order.status !== 'retirada')
            .length,
        ),
        subtext: 'Dados carregados da API',
        icon: 'trending-up',
        variant: 'neutro',
      },
    ];
  }

  readonly searchTerm = signal('');
  readonly selectedCategory = signal<'todos' | OrderCategory>('todos');
  readonly selectedStatus = signal<'todos' | OrderStatus>('todos');
  readonly pendingCount = computed(
    () => this.orders().filter((o) => o.status === 'pendente').length,
  );
  readonly productionCount = computed(
    () => this.orders().filter((o) => o.status === 'producao').length,
  );
  readonly readyCount = computed(() => this.orders().filter((o) => o.status === 'retirada').length);
  readonly cancelledCount = computed(
    () => this.orders().filter((o) => o.status === 'cancelado').length,
  );
  readonly activeCount = computed(
    () =>
      this.orders().filter((o) => ['pedido_feito', 'em_producao'].includes(o.apiOrder.status))
        .length,
  );

  readonly filteredOrders = computed(() => {
    const term = this.searchTerm().trim().toLowerCase();
    const status = this.selectedStatus();

    return this.orders().filter((order) => {
      const matchesTerm =
        !term ||
        order.id.toLowerCase().includes(term) ||
        order.customer.toLowerCase().includes(term) ||
        order.item.toLowerCase().includes(term);
      const matchesStatus = status === 'todos' || order.status === status;
      return matchesTerm && matchesStatus;
    });
  });
  readonly paginatedOrders = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize;
    return this.filteredOrders().slice(start, start + this.pageSize);
  });
  readonly totalPages = computed(() => Math.ceil(this.filteredOrders().length / this.pageSize));

  ngOnInit(): void {
    this.loadOrders();
    this.domainApi.getProducts().subscribe({
      next: (products) => this.products.set(products),
      error: (error: unknown) => {
        console.error('Falha ao carregar produtos.', error);
      },
    });
    this.domainApi.getRecipes().subscribe({
      next: (recipes) => this.recipes.set(recipes),
      error: (error: unknown) => {
        this.createError.set(
          `Não foi possível carregar as receitas para o cadastro. ${this.errorDetail(error)}`,
        );
        console.error('Falha ao carregar as receitas para o cadastro de pedido.', error);
      },
    });
  }

  setCategory(category: 'todos' | OrderCategory): void {
    this.selectedCategory.set(category);
    this.currentPage.set(1);
  }

  setStatus(status: 'todos' | OrderStatus): void {
    this.selectedStatus.set(status);
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

  completeOrder(order: OrderRow): void {
    if (this.operationInProgress()) {
      return;
    }

    switch (order.apiOrder.status) {
      case 'em_producao':
        this.actionError.set(null);
        this.analyzeOrder(order, (analysis) => {
          if (analysis.ausencias.length > 0) {
            this.handleActionError(
              `Não é possível concluir a produção: ${analysis.ausencias.map((item) => item.motivo).join(' ')}`,
            );
            return;
          }
          if (analysis.ingredientes_insuficientes.length > 0) {
            const names = analysis.ingredientes_insuficientes.map((item) => item.nome).join(', ');
            this.handleActionError(`Saldo insuficiente para concluir a produção: ${names}.`);
            return;
          }
          this.selectedOrder.set({ ...order, analysis });
          this.isCompleteModalOpen.set(true);
        });
        return;
      case 'pedido_feito':
        this.validateAndStartOrder(order);
        return;
      case 'producao_concluida':
        if (order.apiOrder.tipo === 'externo') {
          this.consumeOrderStock(order);
        } else {
          this.finishInternalOrder(order);
        }
        return;
      default:
        this.actionError.set('Esta ação não está disponível para o status atual do pedido.');
        return;
    }
  }

  confirmOrderCompletion(): void {
    const order = this.selectedOrder();
    const payload = this.completeProductionModal?.submittedPayload;

    if (!order || !payload || this.operationInProgress()) {
      if (!payload) {
        this.handleActionError('Os dados da conclusão não foram informados.');
      }
      return;
    }

    this.actionError.set(null);
    this.operationInProgress.set(true);
    this.domainApi.completeProduction(order.apiOrder.id_pedido, payload).subscribe({
      next: ({ pedido }) => {
        this.replaceOrder(pedido);
        this.operationInProgress.set(false);
        this.closeCompleteModal();
        this.refreshOrders();
      },
      error: (error: unknown) => {
        this.handleActionError('Não foi possível concluir a produção.', error);
      },
    });
  }

  closeCompleteModal(): void {
    this.isCompleteModalOpen.set(false);
    this.selectedOrder.set(null);
  }

  cancelOrder(order: OrderRow): void {
    if (this.operationInProgress()) {
      return;
    }

    this.actionError.set(null);
    if (order.apiOrder.status === 'concluido' || order.apiOrder.status === 'cancelado') {
      this.actionError.set('Pedidos concluídos ou cancelados não podem ser cancelados.');
      return;
    }

    this.analyzeOrder(order, (analysis) => {
      this.selectedOrder.set({ ...order, analysis });
      this.isCancelModalOpen.set(true);
    });
  }

  confirmOrderCancellation(): void {
    const order = this.selectedOrder();
    const payload = this.cancelProductionModal?.submittedPayload;

    if (!order || !payload || this.operationInProgress()) {
      if (!payload) {
        this.handleActionError('Os dados do cancelamento não foram informados.');
      }
      return;
    }

    this.actionError.set(null);
    this.operationInProgress.set(true);
    this.domainApi.cancelOrder(order.apiOrder.id_pedido, payload).subscribe({
      next: () => {
        this.updateOrderStatus(order.apiOrder.id_pedido, 'cancelado');
        this.operationInProgress.set(false);
        this.closeCancelModal();
        this.refreshOrders();
      },
      error: (error: unknown) => {
        this.handleActionError('Não foi possível cancelar o pedido.', error);
      },
    });
  }

  handleGreetingAction(action: PageAction): void {
    if (action.label === '+ Novo Pedido') {
      this.createError.set(null);
      this.isCreateModalOpen.set(true);
      return;
    }
  }

  closeCancelModal(): void {
    this.isCancelModalOpen.set(false);
    this.selectedOrder.set(null);
  }

  closeCreateModal(): void {
    if (this.creationInProgress()) {
      return;
    }
    this.isCreateModalOpen.set(false);
    this.createError.set(null);
  }

  createOrder(payload: OrderCreationPayload): void {
    if (this.creationInProgress()) {
      return;
    }

    this.creationInProgress.set(true);
    this.createError.set(null);
    this.domainApi.createOrder(payload).subscribe({
      next: () => {
        this.creationInProgress.set(false);
        this.isCreateModalOpen.set(false);
        this.loadOrders();
      },
      error: (error: unknown) => {
        this.creationInProgress.set(false);
        this.createError.set(`Não foi possível cadastrar o pedido. ${this.errorDetail(error)}`);
        console.error('Falha ao cadastrar pedido.', error);
      },
    });
  }

  editOrder(order: OrderRow): void {
    if (['concluido', 'cancelado'].includes(order.apiOrder.status)) {
      this.actionError.set('Pedidos concluídos ou cancelados não podem ser editados.');
      return;
    }
    this.createError.set(null);
    this.selectedOrder.set(order);
    this.isEditModalOpen.set(true);
  }

  closeEditModal(): void {
    this.isEditModalOpen.set(false);
    this.selectedOrder.set(null);
    this.createError.set(null);
  }

  handleOrderEdit(payload: OrderCreationPayload): void {
    const order = this.selectedOrder();
    if (!order || this.creationInProgress()) {
      return;
    }
    this.creationInProgress.set(true);
    this.createError.set(null);
    this.domainApi.updateOrder(order.apiOrder.id_pedido, payload).subscribe({
      next: () => {
        this.creationInProgress.set(false);
        this.closeEditModal();
        this.loadOrders();
      },
      error: (error: unknown) => {
        this.creationInProgress.set(false);
        this.createError.set(`Não foi possível atualizar o pedido. ${this.errorDetail(error)}`);
        console.error('Falha ao editar pedido.', error);
      },
    });
  }

  private loadOrders(): void {
    this.domainApi.getOrders().subscribe({
      next: (orders) => {
        this.orders.set(orders.map((order) => this.toOrderRow(order)));
        this.loadError.set(null);
        this.currentPage.set(1);
      },
      error: (error: unknown) => {
        this.loadError.set(this.errorDetail(error));
        console.error('Falha ao carregar os pedidos.', error);
      },
    });
  }

  private refreshOrders(): void {
    this.loadOrders();
  }

  // Valida o pedido e pede confirmação antes de iniciar a produção ou baixar o estoque (RNF04).
  private validateAndStartOrder(order: OrderRow): void {
    this.analyzeOrder(order, (analysis) => {
      if (analysis.ausencias.length > 0) {
        this.handleActionError(
          `Não é possível iniciar a produção: ${analysis.ausencias.map((item) => item.motivo).join(' ')}`,
        );
        return;
      }
      const mode =
        order.apiOrder.tipo === 'externo' && !analysis.encaminhar_para_producao
          ? 'estoque'
          : 'producao';
      if (mode === 'producao' && analysis.ingredientes_insuficientes.length > 0) {
        const names = analysis.ingredientes_insuficientes.map((item) => item.nome).join(', ');
        this.handleActionError(`Estoque insuficiente para iniciar a produção: ${names}.`);
        return;
      }
      this.pendingStart.set({ order, analysis, mode });
    });
  }

  confirmStart(): void {
    const pending = this.pendingStart();
    if (!pending || this.operationInProgress()) {
      return;
    }
    const orderId = pending.order.apiOrder.id_pedido;
    const request =
      pending.mode === 'estoque'
        ? this.domainApi.consumeStock(orderId)
        : this.domainApi.startProduction(orderId);
    this.actionError.set(null);
    this.operationInProgress.set(true);
    request.subscribe({
      next: (updatedOrder) => {
        this.pendingStart.set(null);
        this.finishActionWithOrder(updatedOrder);
      },
      error: (error: unknown) =>
        this.handleActionError(
          pending.mode === 'estoque'
            ? 'Não foi possível consumir o estoque do pedido.'
            : 'Não foi possível iniciar a produção.',
          error,
        ),
    });
  }

  closeStartDialog(): void {
    if (this.operationInProgress()) {
      return;
    }
    this.pendingStart.set(null);
    this.actionError.set(null);
  }

  productName(productId: number | null): string {
    if (productId === null) {
      return 'Item sem produto vinculado';
    }
    return (
      this.products().find((product) => product.id_produto === productId)?.nome ??
      `Produto #${productId}`
    );
  }

  private analyzeOrder(order: OrderRow, onSuccess: (analysis: ProductionAnalysis) => void): void {
    if (this.operationInProgress()) {
      return;
    }
    this.operationInProgress.set(true);
    this.domainApi.analyzeProduction(order.apiOrder.id_pedido).subscribe({
      next: (analysis) => {
        this.operationInProgress.set(false);
        this.actionError.set(null);
        onSuccess(analysis);
      },
      error: (error: unknown) => {
        this.handleActionError('Não foi possível carregar os dados de produção do pedido.', error);
      },
    });
  }

  private consumeOrderStock(order: OrderRow): void {
    this.operationInProgress.set(true);
    this.domainApi.consumeStock(order.apiOrder.id_pedido).subscribe({
      next: (updatedOrder) => this.finishActionWithOrder(updatedOrder),
      error: (error: unknown) =>
        this.handleActionError('Não foi possível consumir o estoque do pedido.', error),
    });
  }

  private finishInternalOrder(order: OrderRow): void {
    this.operationInProgress.set(true);
    this.domainApi.finishInternalOrder(order.apiOrder.id_pedido).subscribe({
      next: (updatedOrder) => this.finishActionWithOrder(updatedOrder),
      error: (error: unknown) =>
        this.handleActionError('Não foi possível finalizar o pedido interno.', error),
    });
  }

  private finishActionWithOrder(order: ApiOrder): void {
    this.replaceOrder(order);
    this.operationInProgress.set(false);
    this.actionError.set(null);
    this.refreshOrders();
  }

  private replaceOrder(order: ApiOrder): void {
    this.orders.update((currentOrders) =>
      currentOrders.map((current) =>
        current.apiOrder.id_pedido === order.id_pedido ? this.toOrderRow(order) : current,
      ),
    );
  }

  private updateOrderStatus(orderId: number, status: ApiOrder['status']): void {
    this.orders.update((currentOrders) =>
      currentOrders.map((current) =>
        current.apiOrder.id_pedido === orderId
          ? this.toOrderRow({ ...current.apiOrder, status })
          : current,
      ),
    );
  }

  private handleActionError(message: string, error?: unknown): void {
    this.operationInProgress.set(false);
    this.actionError.set(error === undefined ? message : `${message} ${this.errorDetail(error)}`);
    console.error(message, error);
  }

  private toOrderRow(order: ApiOrder): OrderRow {
    const baseNames = order.itens.map((item) => this.itemName(item));
    const itemNames = order.itens.map((item, index) => {
      const quantity = item.quantidade ?? item.quantidade_peso;
      return `${baseNames[index]}${quantity === null || quantity === undefined ? '' : ` (${quantity})`}`;
    });
    const total = this.toNumber(order.valor_total);
    const balance = Math.max(0, total - this.toNumber(order.valor_sinal));
    const status = this.toViewStatus(order.status);
    const statusDetail: Record<ApiOrder['status'], string> = {
      pedido_feito: 'Aguardando validação',
      em_producao: 'Produção iniciada',
      producao_concluida: 'Aguardando retirada ou consumo',
      concluido: 'Pedido finalizado',
      cancelado: 'Pedido cancelado',
    };

    return {
      id: `#${order.id_pedido}`,
      customer:
        order.cliente_nome ??
        (order.cliente === null
          ? order.tipo === 'interno'
            ? 'Pedido interno'
            : 'Cliente não informado'
          : `Cliente #${order.cliente}`),
      phone: order.cliente_telefone || 'Contato não informado',
      address: order.endereco_entrega ?? 'Endereço não informado',
      item: itemNames.join(', ') || 'Itens não informados',
      reuseName: baseNames.length > 0 ? `${baseNames[0]} reaproveitado` : '',
      category: this.toCategory(itemNames.join(' ')),
      total: this.formatCurrency(total),
      payment:
        order.valor_sinal !== '0.00' && order.valor_sinal !== '0'
          ? `Sinal: ${this.formatCurrency(this.toNumber(order.valor_sinal))}`
          : (order.forma_pagamento ?? 'Pagamento não informado'),
      status,
      statusLabel: this.statusLabel(status),
      schedule: this.formatSchedule(order.data_entrega, order.horario_entrega),
      detail:
        balance > 0 && order.status !== 'cancelado'
          ? `${statusDetail[order.status]} · Saldo ${this.formatCurrency(balance)}`
          : statusDetail[order.status],
      action: this.actionLabel(order),
      image: '/images/auth-cake.jpg',
      apiOrder: order,
      analysis: order.analise ?? null,
    };
  }

  private itemName(item: ApiOrder['itens'][number]): string {
    if (item.produto_nome) {
      return item.produto_nome;
    }
    if (item.receita_nome) {
      return item.receita_nome;
    }
    if (item.produto !== null) {
      return this.productName(item.produto);
    }
    return item.receita !== null ? `Receita #${item.receita}` : 'Item sem produto vinculado';
  }

  private toViewStatus(status: ApiOrder['status']): OrderStatus {
    switch (status) {
      case 'pedido_feito':
        return 'pendente';
      case 'em_producao':
        return 'producao';
      case 'producao_concluida':
      case 'concluido':
        return 'retirada';
      case 'cancelado':
        return 'cancelado';
    }
  }

  private statusLabel(status: OrderStatus): string {
    const labels: Record<OrderStatus, string> = {
      retirada: 'Pronto / concluído',
      producao: 'Em produção',
      pendente: 'Pendente',
      cancelado: 'Cancelado',
    };
    return labels[status];
  }

  private actionLabel(order: ApiOrder): string {
    switch (order.status) {
      case 'pedido_feito':
        return 'Iniciar Produção';
      case 'em_producao':
        return 'Concluir Produção';
      case 'producao_concluida':
        return order.tipo === 'externo' ? 'Consumir estoque' : 'Concluir pedido';
      case 'concluido':
      case 'cancelado':
        return 'Ver Detalhes';
    }
  }

  private toCategory(value: string): OrderCategory | null {
    const normalized = value.toLocaleLowerCase('pt-BR');
    if (
      normalized.includes('brigadeiro') ||
      normalized.includes('doce') ||
      normalized.includes('docinho')
    ) {
      return 'doces';
    }
    if (normalized.includes('kit') || normalized.includes('festa')) {
      return 'kits';
    }
    if (normalized.includes('bolo') || normalized.includes('torta')) {
      return 'bolos';
    }
    return null;
  }

  private formatSchedule(date: string | null, time: string | null): string {
    if (!date) {
      return 'Entrega não informada';
    }
    const parsedDate = new Date(`${date}T00:00:00`);
    const formattedDate = Number.isNaN(parsedDate.getTime())
      ? date
      : parsedDate.toLocaleDateString('pt-BR');
    return time ? `${formattedDate} · ${time.slice(0, 5)}` : formattedDate;
  }

  private toNumber(value: string | null): number {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  private formatCurrency(value: number): string {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  private errorDetail(error: unknown): string {
    if (typeof error === 'object' && error !== null && 'error' in error) {
      const detail = error.error;
      if (typeof detail === 'string') {
        return detail;
      }
      if (detail !== null && detail !== undefined) {
        try {
          return JSON.stringify(detail) ?? 'Erro desconhecido ao consultar a API.';
        } catch {
          return 'Erro desconhecido ao consultar a API.';
        }
      }
    }
    if (error instanceof Error) {
      return error.message;
    }
    if (typeof error === 'string') {
      return error;
    }
    try {
      return JSON.stringify(error) ?? 'Erro desconhecido ao consultar a API.';
    } catch {
      return 'Erro desconhecido ao consultar a API.';
    }
  }
}
