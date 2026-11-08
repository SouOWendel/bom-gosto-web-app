import { Component, HostListener, input, OnInit, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  LucideAlertTriangle,
  LucideInfo,
  LucideLockKeyhole,
  LucidePackage,
  LucideTrash2,
  LucideX,
  LucideDynamicIcon,
  provideLucideIcons,
} from '@lucide/angular';
import { InputTextComponent } from '../input-text/input-text.component';
import { ButtonComponent } from '../button/button.component';
import {
  CancelOrderPayload,
  ProductionAnalysis,
  ProductionConsumption,
} from '../../../core/models/api.model';

interface Ingredient {
  id: number;
  name: string;
  quantity: string;
  observation: string;
}

export interface CancelProductionOrder {
  id: string;
  customer?: string;
  item: string;
  analysis: ProductionAnalysis | null;
}

@Component({
  selector: 'app-cancel-production-modal',
  standalone: true,
  imports: [FormsModule, InputTextComponent, ButtonComponent, LucideDynamicIcon],
  providers: [
    provideLucideIcons(
      LucideAlertTriangle,
      LucideInfo,
      LucideLockKeyhole,
      LucidePackage,
      LucideTrash2,
      LucideX,
    ),
  ],
  templateUrl: './cancel-production-modal.component.html',
  styleUrls: ['./cancel-production-modal.component.scss'],
})
export class CancelProductionModalComponent implements OnInit {
  readonly order = input<CancelProductionOrder | null>(null);
  reuseProductName = '';
  reuseQuantity = '';
  reuseExpiration = '';
  reuseCost = '';
  reusePrice = '';

  readonly closed = output<void>();
  readonly confirmed = output<void>();
  submittedPayload: CancelOrderPayload | null = null;

  readonly ingredients: Ingredient[] = [];

  selectedDestination: 'stock' | 'discard' = 'stock';

  ngOnInit(): void {
    const order = this.order();
    if (!order?.analysis) {
      console.error('Não há análise de produção disponível para cancelar este pedido.');
      return;
    }

    this.ingredients.push(
      ...order.analysis.ingredientes.map((ingredient) => ({
        id: ingredient.id_ingrediente,
        name: ingredient.nome,
        quantity: '',
        observation: `Previsto: ${ingredient.necessario} · Disponível: ${ingredient.disponivel}`,
      })),
    );
    this.reuseProductName = order.item ? `${order.item} reaproveitado` : '';
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  close(): void {
    this.closed.emit();
  }

  confirm(): void {
    const consumos: ProductionConsumption[] = [];
    for (const ingredient of this.ingredients) {
      if (!ingredient.quantity.trim()) {
        console.error(`Informe o consumo de ${ingredient.name}; use zero se não houve consumo.`);
        return;
      }
      const quantity = Number(ingredient.quantity);
      if (!Number.isFinite(quantity) || quantity < 0) {
        console.error(`Quantidade inválida para o ingrediente ${ingredient.name}.`);
        return;
      }
      consumos.push({
        ingrediente_id: ingredient.id,
        quantidade: String(quantity),
      });
    }

    const payload: CancelOrderPayload = {
      consumos,
      destino: this.selectedDestination === 'stock' ? 'estoque' : 'descarte',
    };

    if (this.selectedDestination === 'stock') {
      const quantity = this.toDecimal(this.reuseQuantity);
      const cost = this.toDecimal(this.reuseCost);
      const salePrice = this.toDecimal(this.reusePrice);
      if (
        !this.reuseProductName.trim() ||
        !this.reuseExpiration ||
        quantity === null ||
        Number(quantity) <= 0 ||
        cost === null ||
        Number(cost) < 0 ||
        salePrice === null ||
        Number(salePrice) < 0
      ) {
        console.error('Preencha dados válidos do produto reaproveitado para enviá-lo ao estoque.');
        return;
      }
      payload.produto_aproveitado = {
        nome: this.reuseProductName.trim(),
        quantidade: quantity,
        data_validade: this.reuseExpiration,
        custo: cost,
        preco_venda: salePrice,
      };
    }

    this.submittedPayload = payload;
    this.confirmed.emit();
  }

  private toDecimal(value: string): string | null {
    const normalized = value.trim().includes(',')
      ? value.trim().replace(/\./g, '').replace(',', '.')
      : value.trim();
    if (!normalized || !Number.isFinite(Number(normalized))) {
      return null;
    }
    return normalized;
  }
}
