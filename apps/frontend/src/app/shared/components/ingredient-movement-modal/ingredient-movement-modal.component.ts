import { Component, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonComponent } from '../button/button.component';
import { InputTextComponent } from '../input-text/input-text.component';
import { Ingredient } from '../../../core/models/api.model';

export interface IngredientMovementPayload {
  tipo: 'entrada' | 'saida';
  quantidade: string;
  custo_unitario?: string | null;
  data_validade?: string | null;
}

@Component({
  selector: 'app-ingredient-movement-modal',
  standalone: true,
  imports: [FormsModule, ButtonComponent, InputTextComponent],
  templateUrl: './ingredient-movement-modal.component.html',
  styleUrls: ['./ingredient-movement-modal.component.scss'],
})
export class IngredientMovementModalComponent {
  readonly ingredient = input.required<Ingredient>();
  readonly type = input.required<'entrada' | 'saida'>();
  readonly apiError = input<string | null>(null);
  readonly closed = output<void>();
  readonly submitted = output<IngredientMovementPayload>();

  quantity = '';
  unitCost = '';
  expirationDate = '';
  errorMessage = '';

  close(): void {
    this.closed.emit();
  }

  submit(): void {
    const quantity = this.quantity.trim().replace(',', '.');
    if (!quantity || !Number.isFinite(Number(quantity)) || Number(quantity) <= 0) {
      this.errorMessage = 'Informe uma quantidade maior que zero.';
      return;
    }

    if (this.type() === 'entrada' && this.unitCost.trim()) {
      const cost = Number(this.unitCost.trim().replace(',', '.'));
      if (!Number.isFinite(cost) || cost < 0) {
        this.errorMessage = 'Informe um custo unitário válido.';
        return;
      }
    }

    this.submitted.emit({
      tipo: this.type(),
      quantidade: quantity,
      ...(this.type() === 'entrada'
        ? {
            custo_unitario: this.unitCost.trim().replace(',', '.') || null,
            data_validade: this.expirationDate || null,
          }
        : {}),
    });
  }
}
