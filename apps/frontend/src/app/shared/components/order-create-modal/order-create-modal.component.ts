import { CommonModule } from '@angular/common';
import { Component, effect, input, OnInit, output } from '@angular/core';
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
import { ButtonComponent } from '../button/button.component';
import { InputTextComponent } from '../input-text/input-text.component';

interface OrderItemForm {
  kind: 'produto' | 'receita';
  referenceId: number | null;
  quantity: string;
  unitPrice: string;
}

@Component({
  selector: 'app-order-create-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, ButtonComponent, InputTextComponent, LucideDynamicIcon],
  providers: [provideLucideIcons(LucidePlus, LucideTrash2, LucideX)],
  templateUrl: './order-create-modal.component.html',
  styleUrls: ['./order-create-modal.component.scss'],
})
export class OrderCreateModalComponent implements OnInit {
  readonly recipes = input<Recipe[]>([]);
  readonly productsList = input<Product[]>([]);
  readonly orderToEdit = input<Order | null>(null);
  readonly apiError = input<string | null>(null);
  readonly closed = output<void>();
  readonly submitted = output<OrderCreationPayload>();

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

  ngOnInit(): void {
    const order = this.orderToEdit();
    if (order) {
      this.populate(order);
    }
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

    if (order.itens && order.itens.length > 0) {
      this.items = order.itens.map((item) => ({
        kind: item.produto ? 'produto' : 'receita',
        referenceId: item.produto ?? item.receita ?? null,
        quantity: String(item.quantidade ?? item.quantidade_peso ?? 1),
        unitPrice: String(item.preco_unitario ?? ''),
      }));
    }
  }

  get products(): Array<{ id: number; label: string }> {
    const list = this.productsList();
    if (list && list.length > 0) {
      return list.map((p) => ({
        id: p.id_produto,
        label: `${p.nome} (R$ ${p.preco_venda})`,
      }));
    }
    const products = new Map<number, string>();
    for (const recipe of this.recipes()) {
      for (const product of recipe.produtos ?? []) {
        products.set(product.produto, `Produto #${product.produto}`);
      }
    }
    return [...products.entries()].map(([id, label]) => ({ id, label }));
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

  close(): void {
    this.closed.emit();
  }

  submit(): void {
    const validationError = this.validate();
    if (validationError) {
      this.errorMessage = validationError;
      return;
    }

    const payload: OrderCreationPayload = {
      tipo: this.tipo,
      subtipo: this.tipo === 'externo' ? this.subtipo : null,
      data_entrega: this.deliveryDate || null,
      horario_entrega: this.deliveryTime || null,
      valor_total: this.toDecimal(this.total),
      valor_sinal: this.toDecimal(this.deposit),
      endereco_entrega: this.address.trim() || null,
      forma_pagamento: this.paymentMethod || null,
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
      kind: 'receita',
      referenceId: null,
      quantity: '1',
      unitPrice: '',
    };
  }

  private toApiItem(item: OrderItemForm): OrderCreationItem {
    const apiItem: OrderCreationItem = {
      preco_unitario: this.toDecimal(item.unitPrice),
    };
    apiItem[item.kind] = item.referenceId as number;
    apiItem.quantidade = Number(item.quantity);
    return apiItem;
  }

  private validate(): string | null {
    if (
      this.tipo === 'externo' &&
      !this.orderToEdit() &&
      (!this.contactName.trim() || !this.contactPhone.trim())
    ) {
      return 'Informe o nome e o telefone do cliente.';
    }
    if (
      this.tipo === 'externo' &&
      this.subtipo === 'vitrine' &&
      this.items.some((item) => item.kind !== 'produto')
    ) {
      return 'Pedidos de vitrine precisam usar produtos prontos.';
    }
    if (this.items.some((item) => item.referenceId === null || Number(item.quantity) <= 0)) {
      return 'Informe um item válido e uma quantidade maior que zero.';
    }
    if (
      this.items.some((item) => {
        const price = Number(this.toDecimal(item.unitPrice));
        return !Number.isFinite(price) || price < 0;
      })
    ) {
      return 'Informe um preço unitário válido para cada item.';
    }
    const total = Number(this.toDecimal(this.total));
    const deposit = Number(this.toDecimal(this.deposit));
    if (!Number.isFinite(total) || total < 0) {
      return 'Informe um valor total válido.';
    }
    if (!Number.isFinite(deposit) || deposit < 0 || deposit > total) {
      return 'O sinal deve estar entre zero e o valor total.';
    }
    if (this.tipo === 'externo' && deposit !== 0 && Math.abs(deposit - total / 2) > 0.001) {
      return 'Para pedidos externos, o sinal deve ser zero ou metade do total.';
    }
    return null;
  }

  private toDecimal(value: string): string {
    const normalized = value.trim().replace(/[R$\s]/g, '');
    if (normalized.includes(',')) {
      return normalized.replace(/\./g, '').replace(',', '.');
    }
    return normalized;
  }
}
