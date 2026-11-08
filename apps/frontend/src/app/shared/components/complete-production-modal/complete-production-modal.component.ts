import { Component, HostListener, input, OnInit, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LucideCheck, LucideDynamicIcon, provideLucideIcons } from '@lucide/angular';
import { InputTextComponent } from '../input-text/input-text.component';
import { ButtonComponent } from '../button/button.component';
import {
  CompleteProductionPayload,
  ProductionAnalysis,
  ProductionConsumption,
} from '../../../core/models/api.model';

interface ProductionIngredient {
  id: number;
  name: string;
  lot: string;
  theoreticalQuantity: string;
  quantity: string;
  availableQuantity: string;
  unit: string;
}

interface ProductionOrder {
  id: string;
  item: string;
  analysis: ProductionAnalysis | null;
}

@Component({
  selector: 'app-complete-production-modal',
  standalone: true,
  imports: [FormsModule, InputTextComponent, ButtonComponent, LucideDynamicIcon],
  providers: [provideLucideIcons(LucideCheck)],
  templateUrl: './complete-production-modal.component.html',
  styleUrls: ['./complete-production-modal.component.scss'],
})
export class CompleteProductionModalComponent implements OnInit {
  readonly order = input.required<ProductionOrder>();
  readonly closed = output<void>();
  readonly confirmed = output<void>();
  submittedPayload: CompleteProductionPayload | null = null;

  readonly ingredients: ProductionIngredient[] = [];

  expirationDate = '';

  ngOnInit(): void {
    const analysis = this.order().analysis;
    if (!analysis) {
      console.error('Não há análise de produção disponível para concluir este pedido.');
      return;
    }

    this.ingredients.push(
      ...analysis.ingredientes.map((ingredient) => ({
        id: ingredient.id_ingrediente,
        name: ingredient.nome,
        lot: `Disponível: ${ingredient.disponivel}`,
        theoreticalQuantity: ingredient.necessario,
        quantity: '',
        availableQuantity: ingredient.disponivel,
        unit: '',
      })),
    );
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  close(): void {
    this.closed.emit();
  }

  confirm(): void {
    if (!this.expirationDate || this.ingredients.length === 0) {
      console.error('Informe a validade e os consumos reais antes de concluir a produção.');
      return;
    }

    const consumos: ProductionConsumption[] = [];
    for (const ingredient of this.ingredients) {
      if (!ingredient.quantity.trim()) {
        console.error(`Informe o consumo real de ${ingredient.name}; use zero se não houve consumo.`);
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

    this.submittedPayload = {
      data_validade: this.expirationDate,
      consumos,
    };
    this.confirmed.emit();
  }
}
