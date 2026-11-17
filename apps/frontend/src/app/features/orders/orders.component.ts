import { Component, computed, inject, OnInit, signal, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
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
import { ButtonComponent } from '../../shared/components/button/button.component';
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
import { apiErrorMessage } from '../../core/utils/api-error';
import { formatCurrency, formatDate, formatQuantity, toNumber } from '../../core/utils/format';
import { hasPayment } from '../../core/utils/order-payment';
import { ORDER_STATUS_LABELS } from '../../core/models/order-status';

type OrderStatus = 'retirada' | 'producao' | 'pendente' | 'cancelado';

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
  // Nome sugerido para o produto reaproveitado no cancelamento.
  reuseName: string;
  total: string;
  payment: string;
  status: OrderStatus;
  statusLabel: string;
  schedule: string;
  modality: string;
  detail: string;
  action: string;
  // Dica mostrada ao passar o mouse no botão de ação.
  actionHint: string | null;
  apiOrder: ApiOrder;
  analysis: ProductionAnalysis | null;
}

@Component({
  selector: 'app-orders',
  standalone: true,
  imports: [
    TablePaginationComponent,
    LucideDynamicIcon,
    PageGreetingComponent,
    MetricCardsComponent,
    CancelProductionModalComponent,
    CompleteProductionModalComponent,
    OrderCreateModalComponent,
    ConfirmDialogComponent,
    ButtonComponent,
  ],
  providers: [
    provideLucideIcons(LucideBan, LucideMessageSquare, LucidePencil, LucidePrinter, LucideSearch),
  ],
  templateUrl: './orders.component.html',
  styleUrls: ['./orders.component.scss'],
})
export class OrdersComponent implements OnInit {
  private readonly domainApi = inject(DomainApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

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
  readonly pendingFinish = signal<OrderRow | null>(null);
  readonly currentPage = signal(1);
  readonly pageSize = 6;
  readonly formatQuantity = formatQuantity;

  // Por enquanto, iniciar a produção de um pedido externo marca o sinal como pago
  // (regra provisória do MVP; o registro em Finanças da RN13 fica para depois).
  depositReminder(order: OrderRow): string | null {
    return this.depositNotice(order.apiOrder);
  }

  private depositNotice(order: ApiOrder): string | null {
    if (!hasPayment(order) || order.subtipo === 'vitrine' || order.status !== 'pedido_feito') {
      return null;
    }
    const deposit = toNumber(order.valor_sinal);
    return deposit > 0
      ? `Ao iniciar a produção, o sinal de ${formatCurrency(deposit)} será marcado como pago.`
      : 'Nenhum sinal registrado neste pedido. Confirme o pagamento com o cliente antes de iniciar.';
  }
  @ViewChild(CancelProductionModalComponent)
  private cancelProductionModal?: CancelProductionModalComponent;
  @ViewChild(CompleteProductionModalComponent)
  private completeProductionModal?: CompleteProductionModalComponent;

  readonly greetingActions: PageAction[] = [
    { id: 'novo-pedido', label: 'Novo pedido', icon: 'plus', variant: 'primary' },
  ];

  readonly statusTabs: Array<{ value: 'todos' | OrderStatus; label: string }> = [
    { value: 'todos', label: 'Todos' },
    { value: 'pendente', label: 'Pendentes' },
    { value: 'producao', label: 'Em produção' },
    { value: 'retirada', label: 'Prontos / concluídos' },
    { value: 'cancelado', label: 'Cancelados' },
  ];

  // Mesma cor de status em toda a aplicação (ver .badge em styles.scss).
  readonly statusBadge: Record<OrderStatus, string> = {
    pendente: 'badge--warning',
    producao: 'badge--info',
    retirada: 'badge--success',
    cancelado: 'badge--neutral',
  };

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
  readonly ordersSubtitle = computed(
    () =>
      `${this.orders().length} pedidos cadastrados • ${this.statusCounts().pendente} aguardando produção`,
  );

  readonly summaryCards = computed<MetricCardItem[]>(() => {
    const orders = this.orders();
    const inProduction = orders.filter((order) => order.status === 'producao');
    const ready = orders.filter(
      (order) =>
        order.apiOrder.status === 'producao_concluida' && order.apiOrder.tipo === 'externo',
    ).length;
    const pendingBalance = orders
      .filter((order) => order.status !== 'cancelado' && order.status !== 'retirada')
      .reduce((total, order) => total + this.balanceDue(order.apiOrder), 0);
    const productionValue = inProduction.reduce(
      (total, order) => total + toNumber(order.apiOrder.valor_total),
      0,
    );

    return [
      {
        label: 'Em produção',
        value: formatCurrency(productionValue),
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
        value: formatCurrency(pendingBalance),
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
        subtext: 'Sem contar os cancelados',
        icon: 'trending-up',
        variant: 'neutro',
      },
    ];
  });

  readonly searchTerm = signal('');
  readonly selectedStatus = signal<'todos' | OrderStatus>('todos');

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
          `Não foi possível carregar as receitas para o cadastro. ${apiErrorMessage(error)}`,
        );
        console.error('Falha ao carregar as receitas para o cadastro de pedido.', error);
      },
    });
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
        // Baixa de estoque e conclusão são definitivas: pede confirmação (RNF04).
        this.actionError.set(null);
        this.pendingFinish.set(order);
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
        this.loadOrders();
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
        this.loadOrders();
      },
      error: (error: unknown) => {
        this.handleActionError('Não foi possível cancelar o pedido.', error);
      },
    });
  }

  handleGreetingAction(action: PageAction): void {
    if (action.id === 'novo-pedido') {
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
        this.createError.set(`Não foi possível cadastrar o pedido. ${apiErrorMessage(error)}`);
        console.error('Falha ao cadastrar pedido.', error);
      },
    });
  }

  // Pedidos anteriores ao catálogo de produtos têm item com receita e ficam como leitura.
  // Mesma regra da API: basta um item com receita, mesmo que também tenha produto.
  isLegacyOrder(order: OrderRow): boolean {
    return order.apiOrder.itens.some((item) => item.receita != null);
  }

  addProduct(product: Product): void {
    this.products.update((list) => [...list, product]);
  }

  editOrder(order: OrderRow): void {
    if (['concluido', 'cancelado'].includes(order.apiOrder.status)) {
      this.actionError.set('Pedidos concluídos ou cancelados não podem ser editados.');
      return;
    }
    if (this.isLegacyOrder(order)) {
      this.actionError.set('Pedidos antigos com item de receita ficam somente para leitura.');
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
        this.createError.set(`Não foi possível atualizar o pedido. ${apiErrorMessage(error)}`);
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
        this.runRequestedAction();
      },
      error: (error: unknown) => {
        this.loadError.set(apiErrorMessage(error));
        console.error('Falha ao carregar os pedidos.', error);
      },
    });
  }

  // O Início abre /pedidos?acao=<id> para que a ação passe pelas mesmas validações daqui.
  private runRequestedAction(): void {
    const requested = Number(this.route.snapshot.queryParamMap.get('acao'));
    if (!requested) {
      return;
    }
    void this.router.navigate([], { queryParams: { acao: null }, replaceUrl: true });
    const row = this.orders().find((order) => order.apiOrder.id_pedido === requested);
    if (row) {
      this.completeOrder(row);
    } else {
      this.actionError.set(`Pedido #${requested} não encontrado.`);
    }
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
      // Vitrine nunca vai para a Produção: sem saldo pronto, não há o que atender.
      if (order.apiOrder.subtipo === 'vitrine' && analysis.encaminhar_para_producao) {
        this.handleActionError(
          'Não há produto pronto suficiente no estoque para atender este pedido de vitrine.',
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

  confirmFinish(): void {
    const order = this.pendingFinish();
    if (!order || this.operationInProgress()) {
      return;
    }
    if (order.apiOrder.tipo === 'externo') {
      this.consumeOrderStock(order);
    } else {
      this.finishInternalOrder(order);
    }
  }

  closeFinishDialog(): void {
    if (this.operationInProgress()) {
      return;
    }
    this.pendingFinish.set(null);
    this.actionError.set(null);
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
    this.pendingFinish.set(null);
    this.replaceOrder(order);
    this.operationInProgress.set(false);
    this.actionError.set(null);
    this.loadOrders();
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
    this.actionError.set(error === undefined ? message : `${message} ${apiErrorMessage(error)}`);
    console.error(message, error);
  }

  private toOrderRow(order: ApiOrder): OrderRow {
    const baseNames = order.itens.map((item) => this.itemName(item));
    const itemNames = order.itens.map((item, index) => {
      // Mostra unidades e peso juntos quando houver os dois (ex.: "Bolo (1 · 1,5 kg)").
      const parts = [
        item.quantidade ?? null,
        item.quantidade_peso ? `${Number(item.quantidade_peso).toLocaleString('pt-BR')} kg` : null,
      ].filter((part) => part !== null);
      return `${baseNames[index]}${parts.length ? ` (${parts.join(' · ')})` : ''}`;
    });
    const total = toNumber(order.valor_total);
    const balance = this.balanceDue(order);
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
      total: formatCurrency(total),
      payment: this.paymentLabel(order),
      status,
      statusLabel: ORDER_STATUS_LABELS[order.status],
      schedule: this.formatSchedule(order.data_entrega, order.horario_entrega),
      modality: order.endereco_entrega ? 'Entrega' : 'Retirada',
      detail:
        balance > 0 && order.status !== 'cancelado'
          ? `${statusDetail[order.status]} · Saldo ${formatCurrency(balance)}`
          : statusDetail[order.status],
      action: this.actionLabel(order),
      actionHint: this.depositNotice(order),
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

  private balanceDue(order: ApiOrder): number {
    if (!hasPayment(order)) {
      return 0;
    }
    return Math.max(0, toNumber(order.valor_total) - toNumber(order.valor_sinal));
  }

  private paymentLabel(order: ApiOrder): string {
    if (!hasPayment(order)) {
      return 'Sem pagamento';
    }
    const method = this.paymentMethodLabel(order.forma_pagamento);
    const deposit = toNumber(order.valor_sinal);
    if (deposit <= 0) {
      return method;
    }
    const paid = order.sinal_pago ? ' pago' : '';
    return `Sinal ${formatCurrency(deposit)}${paid} · ${method}`;
  }

  private paymentMethodLabel(method: string | null): string {
    const labels: Record<string, string> = {
      pix: 'Pix',
      cartao: 'Cartão',
      dinheiro: 'Dinheiro',
      pendente: 'Pagamento a definir',
    };
    return method ? (labels[method] ?? method) : 'Pagamento não informado';
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

  private actionLabel(order: ApiOrder): string {
    switch (order.status) {
      case 'pedido_feito':
        // Vitrine sai direto do estoque pronto, sem passar pela Produção.
        return order.subtipo === 'vitrine' ? 'Consumir estoque' : 'Iniciar produção';
      case 'em_producao':
        return 'Concluir produção';
      case 'producao_concluida':
        return order.tipo === 'externo' ? 'Consumir estoque' : 'Concluir pedido';
      case 'concluido':
      case 'cancelado':
        return '';
    }
  }

  private formatSchedule(date: string | null, time: string | null): string {
    if (!date) {
      return 'Entrega não informada';
    }
    const formattedDate = formatDate(date);
    return time ? `${formattedDate} · ${time.slice(0, 5)}` : formattedDate;
  }
}
