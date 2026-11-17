import {
  Component,
  HostListener,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  LucideDynamicIcon,
  LucidePlus,
  LucideTrash2,
  LucideX,
  provideLucideIcons,
} from '@lucide/angular';
import {
  Order,
  OrderCreationItem,
  OrderCreationPayload,
  Product,
  Recipe,
} from '../../../core/models/api.model';
import { DomainApiService } from '../../../core/services/domain-api.service';
import { apiErrorMessage } from '../../../core/utils/api-error';
import { ButtonComponent } from '../button/button.component';
import { InputTextComponent } from '../input-text/input-text.component';
import { ProductCreateModalComponent } from '../product-create-modal/product-create-modal.component';
import {
  formatCurrency,
  formatQuantity,
  parseDecimal,
  toDisplayDecimal,
} from '../../../core/utils/format';

// Todo item é um produto do catálogo; as receitas usadas na produção vêm do produto.
interface OrderItemForm {
  productId: number | null;
  // Quantidade (un) e peso (kg) podem vir juntos, ex.: 1 bolo de 1,5 kg.
  quantity: string;
  weight: string;
  unitPrice: string;
  filling: string;
  decoration: string;
  // Custo já gravado no item, reenviado na edição para não se perder.
  unitCost: string | null;
}

@Component({
  selector: 'app-order-create-modal',
  standalone: true,
  imports: [
    FormsModule,
    ButtonComponent,
    InputTextComponent,
    LucideDynamicIcon,
    ProductCreateModalComponent,
  ],
  providers: [provideLucideIcons(LucidePlus, LucideTrash2, LucideX)],
  templateUrl: './order-create-modal.component.html',
  styleUrls: ['./order-create-modal.component.scss'],
})
export class OrderCreateModalComponent {
  private readonly api = inject(DomainApiService);

  readonly recipes = input<Recipe[]>([]);
  readonly productsList = input<Product[]>([]);
  readonly orderToEdit = input<Order | null>(null);
  readonly apiError = input<string | null>(null);
  readonly closed = output<void>();
  readonly submitted = output<OrderCreationPayload>();
  // Produto cadastrado na hora, para a tela de pedidos atualizar o catálogo.
  readonly productCreated = output<Product>();

  // Cadastro rápido de produto aberto sobre o pedido.
  readonly isProductModalOpen = signal(false);
  readonly productError = signal<string | null>(null);

  tipo: 'interno' | 'externo' = 'externo';
  subtipo: 'vitrine' | 'personalizado' = 'personalizado';
  contactName = '';
  contactPhone = '';
  deliveryDate = '';
  deliveryTime = '';
  address = '';
  paymentMethod = 'pix';
  total = '';
  deposit = '0';
  errorMessage = '';
  items: OrderItemForm[] = [this.newItem()];

  constructor() {
    effect(() => {
      const order = this.orderToEdit();
      if (order) {
        this.populate(order);
      }
    });
  }

  private populate(order: Order): void {
    this.tipo = order.tipo;
    this.subtipo = order.subtipo ?? 'personalizado';
    this.deliveryDate = order.data_entrega ?? '';
    this.deliveryTime = order.horario_entrega ?? '';
    this.address = order.endereco_entrega ?? '';
    this.paymentMethod = order.forma_pagamento ?? 'pix';
    this.total = order.valor_total ?? '';
    this.deposit = order.valor_sinal ?? '0';
    // O contato fica editável para corrigir nome ou telefone digitados errado.
    this.contactName = order.cliente_nome ?? '';
    this.contactPhone = order.cliente_telefone ?? '';

    if (order.itens && order.itens.length > 0) {
      this.items = order.itens.map((item): OrderItemForm => {
        return {
          productId: item.produto ?? null,
          quantity: item.quantidade == null ? '' : String(item.quantidade),
          weight: item.quantidade_peso ? toDisplayDecimal(item.quantidade_peso) : '',
          unitPrice: String(item.preco_unitario ?? ''),
          filling: item.recheio ?? '',
          decoration: item.decoracao ?? '',
          unitCost: item.custo_unitario ?? null,
        };
      });
    }
  }

  // Catálogo completo com o saldo pronto (RN05); produtos sem receita só saem do estoque.
  // computed: os rótulos só são refeitos quando a lista de produtos muda.
  readonly products = computed(() =>
    this.productsList().map((product) => {
      const hasRecipe =
        product.receita !== null || (product.receitas_complementares ?? []).length > 0;
      const stock = `${formatQuantity(product.saldo_disponivel ?? '0')} em estoque`;
      const suffix = hasRecipe ? '' : ' · sem receita';
      return {
        id: product.id_produto,
        label: `${product.nome} (R$ ${product.preco_venda}) · ${stock}${suffix}`,
        inStock: Number(product.saldo_disponivel ?? 0) > 0,
      };
    }),
  );

  // Vitrine vende só o que já está pronto: não produz nem cadastra produto na hora.
  get isShowcase(): boolean {
    return this.tipo === 'externo' && this.subtipo === 'vitrine';
  }

  // Na vitrine, só os produtos com saldo; nos demais tipos, o catálogo inteiro.
  productOptions() {
    return this.isShowcase ? this.products().filter((product) => product.inStock) : this.products();
  }

  // Pedido externo usa primeiro o saldo pronto; no personalizado, o que faltar segue para a
  // Produção (RN06) e só gera aviso (RN03). Na vitrine, a falta impede o cadastro.
  stockWarning(item: OrderItemForm): string | null {
    if (this.tipo !== 'externo') {
      return null;
    }
    const shortage = this.stockShortage(item);
    if (!shortage) {
      return null;
    }
    const { product, available, missing } = shortage;
    if (this.isShowcase) {
      return `Há ${formatQuantity(available)} em estoque. Reduza a quantidade para cadastrar o pedido de vitrine.`;
    }
    const hasRecipe =
      product.receita !== null || (product.receitas_complementares ?? []).length > 0;
    return hasRecipe
      ? `Há ${formatQuantity(available)} em estoque; o restante (${formatQuantity(missing)}) segue para a produção.`
      : `Há ${formatQuantity(available)} em estoque e o produto não tem receita para produzir o restante.`;
  }

  // Falta de saldo do produto do item. Vários itens do mesmo produto dividem o mesmo saldo,
  // como em _saldo_restante na API; a falta é apontada uma vez, no último item desse produto.
  private stockShortage(
    item: OrderItemForm,
  ): { product: Product; available: number; missing: number } | null {
    if (item.productId === null) {
      return null;
    }
    const product = this.productsList().find(
      (candidate) => candidate.id_produto === item.productId,
    );
    if (!product) {
      return null;
    }
    const sameProduct = this.items.filter((candidate) => candidate.productId === item.productId);
    if (sameProduct[sameProduct.length - 1] !== item) {
      return null;
    }
    const requested = sameProduct.reduce(
      (total, candidate) => total + this.requestedAmount(candidate),
      0,
    );
    const available = Number(product.saldo_disponivel ?? 0);
    return requested > available ? { product, available, missing: requested - available } : null;
  }

  // Mesmo critério da API (_quantidade_item): quantidade, ou o peso quando não há quantidade.
  private requestedAmount(item: OrderItemForm): number {
    return Number(item.quantity.trim()) || Number(parseDecimal(item.weight)) || 0;
  }

  // Soma preço x peso (quando informado) ou preço x quantidade de cada item.
  get itemsTotal(): number {
    return this.items.reduce((sum, item) => {
      const price = Number(parseDecimal(item.unitPrice)) || 0;
      const weight = Number(parseDecimal(item.weight)) || 0;
      const quantity = Number(item.quantity) || 0;
      return sum + price * (weight > 0 ? weight : quantity);
    }, 0);
  }

  get totalDiffersFromItems(): boolean {
    const total = Number(parseDecimal(this.total));
    return (
      Number.isFinite(total) &&
      this.total.trim() !== '' &&
      Math.abs(total - this.itemsTotal) > 0.004
    );
  }

  readonly formatCurrency = formatCurrency;

  useItemsTotal(): void {
    this.total = this.itemsTotal.toFixed(2).replace('.', ',');
  }

  addItem(): void {
    this.items = [...this.items, this.newItem()];
  }

  removeItem(index: number): void {
    if (this.items.length === 1) {
      return;
    }
    this.items = this.items.filter((_, itemIndex) => itemIndex !== index);
  }

  openProductModal(): void {
    this.productError.set(null);
    this.isProductModalOpen.set(true);
  }

  closeProductModal(): void {
    this.isProductModalOpen.set(false);
    this.productError.set(null);
  }

  // Cadastra o produto sem sair do pedido e já o seleciona no primeiro item sem
  // produto; se todos já tiverem um, o produto entra em um item novo.
  createProduct(payload: Partial<Product>): void {
    this.api.createProduct(payload).subscribe({
      next: (product) => {
        this.productCreated.emit(product);
        let item = this.items.find((candidate) => candidate.productId === null);
        if (!item) {
          item = this.newItem();
          this.items = [...this.items, item];
        }
        item.productId = product.id_produto;
        if (!item.unitPrice.trim()) {
          // Mesmo formato da API usado ao editar um pedido; a máscara de moeda o converte.
          item.unitPrice = product.preco_venda;
        }
        this.closeProductModal();
      },
      error: (error: unknown) =>
        this.productError.set(`Não foi possível cadastrar o produto. ${apiErrorMessage(error)}`),
    });
  }

  // Com o cadastro rápido aberto, o Esc fecha só ele.
  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.isProductModalOpen()) {
      return;
    }
    this.close();
  }

  close(): void {
    this.closed.emit();
  }

  submit(): void {
    const validationError = this.validate();
    if (validationError) {
      this.errorMessage = validationError;
      return;
    }

    // Reposição interna não tem entrega nem pagamento: limpa o que tiver ficado
    // preenchido antes de trocar o tipo do pedido.
    const isExternal = this.tipo === 'externo';
    const payload: OrderCreationPayload = {
      tipo: this.tipo,
      subtipo: isExternal ? this.subtipo : null,
      data_entrega: (isExternal && this.deliveryDate) || null,
      horario_entrega: (isExternal && this.deliveryTime) || null,
      valor_total: parseDecimal(this.total),
      valor_sinal: parseDecimal(this.deposit),
      endereco_entrega: (isExternal && this.address.trim()) || null,
      forma_pagamento: (isExternal && this.paymentMethod) || null,
      itens: this.items.map((item) => this.toApiItem(item)),
    };

    if (this.tipo === 'externo' && (this.contactName.trim() || this.contactPhone.trim())) {
      payload.contato_nome = this.contactName.trim();
      payload.contato_telefone = this.contactPhone.replace(/\D/g, '');
    }

    this.submitted.emit(payload);
  }

  private newItem(): OrderItemForm {
    return {
      productId: null,
      quantity: '1',
      weight: '',
      unitPrice: '',
      filling: '',
      decoration: '',
      unitCost: null,
    };
  }

  private toApiItem(item: OrderItemForm): OrderCreationItem {
    const apiItem: OrderCreationItem = {
      preco_unitario: parseDecimal(item.unitPrice),
    };
    apiItem.produto = item.productId as number;
    if (item.quantity.trim()) {
      apiItem.quantidade = Number(item.quantity.trim());
    }
    if (item.weight.trim()) {
      apiItem.quantidade_peso = parseDecimal(item.weight);
    }
    apiItem.recheio = item.filling.trim() || null;
    apiItem.decoracao = item.decoration.trim() || null;
    if (item.unitCost !== null) {
      apiItem.custo_unitario = item.unitCost;
    }
    return apiItem;
  }

  private validate(): string | null {
    if (this.tipo === 'externo' && (!this.contactName.trim() || !this.contactPhone.trim())) {
      return 'Informe o nome e o telefone do cliente.';
    }
    if (this.tipo === 'externo' && this.contactPhone.replace(/\D/g, '').length < 10) {
      return 'Informe o telefone com DDD.';
    }
    if (this.items.some((item) => item.productId === null)) {
      return 'Selecione o produto de cada item.';
    }
    for (const item of this.items) {
      const quantity = item.quantity.trim();
      const weight = parseDecimal(item.weight);
      if (!quantity && !weight) {
        return 'Informe a quantidade ou o peso de cada item.';
      }
      if (quantity && (!/^\d+$/.test(quantity) || Number(quantity) <= 0)) {
        return 'A quantidade deve ser um número inteiro maior que zero.';
      }
      if (weight && (!/^\d+(\.\d{1,2})?$/.test(weight) || Number(weight) <= 0)) {
        return 'Informe o peso em kg, maior que zero e com até duas casas decimais.';
      }
    }
    if (this.isShowcase) {
      const missing = this.items
        .map((item) => this.stockShortage(item)?.product.nome)
        .filter((name): name is string => !!name);
      if (missing.length > 0) {
        return `Pedido de vitrine só usa o que há em estoque. Sem saldo suficiente: ${missing.join(', ')}.`;
      }
    }
    if (this.items.some((item) => item.filling.length > 100 || item.decoration.length > 200)) {
      return 'O recheio aceita até 100 caracteres e a decoração, até 200.';
    }
    if (
      this.items.some((item) => {
        const price = Number(parseDecimal(item.unitPrice));
        return !Number.isFinite(price) || price < 0;
      })
    ) {
      return 'Informe um preço unitário válido para cada item.';
    }
    const total = Number(parseDecimal(this.total));
    const deposit = Number(parseDecimal(this.deposit));
    if (!Number.isFinite(total) || total < 0) {
      return 'Informe um valor total válido.';
    }
    // Mesma regra da API: zero (sem sinal) ou um valor positivo menor que o total.
    if (!Number.isFinite(deposit) || deposit < 0 || (deposit > 0 && deposit >= total)) {
      return 'O sinal deve ser zero ou um valor positivo menor que o total.';
    }
    return null;
  }
}
