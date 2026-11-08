import { Component, OnInit, effect, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonComponent } from '../button/button.component';
import { InputTextComponent } from '../input-text/input-text.component';
import { Ingredient } from '../../../core/models/api.model';

export interface IngredientCreationPayload {
  nome: string;
  quantidade_disponivel: string | null;
  quantidade_minima: string | null;
  data_validade: string | null;
  custo_unitario: string | null;
}

@Component({
  selector: 'app-ingredient-create-modal',
  standalone: true,
  imports: [FormsModule, ButtonComponent, InputTextComponent],
  templateUrl: './ingredient-create-modal.component.html',
  styleUrls: ['./ingredient-create-modal.component.scss'],
})
export class IngredientCreateModalComponent implements OnInit {
  readonly closed = output<void>();
  readonly submitted = output<IngredientCreationPayload>();
  readonly apiError = input<string | null>(null);
  readonly ingredientToEdit = input<Ingredient | null>(null);

  name = '';
  availableQuantity = '';
  minimumQuantity = '';
  expirationDate = '';
  unitCost = '';
  errorMessage = '';

  constructor() {
    effect(() => {
      const ing = this.ingredientToEdit();
      if (ing) {
        this.populate(ing);
      }
    });
  }

  ngOnInit(): void {
    const ing = this.ingredientToEdit();
    if (ing) {
      this.populate(ing);
    }
  }

  private populate(ing: Ingredient): void {
    this.name = ing.nome ?? '';
    this.availableQuantity =
      ing.quantidade_disponivel !== null ? String(ing.quantidade_disponivel) : '';
    this.minimumQuantity = ing.quantidade_minima !== null ? String(ing.quantidade_minima) : '';
    this.expirationDate = ing.data_validade ?? '';
    this.unitCost = ing.custo_unitario !== null ? String(ing.custo_unitario) : '';
  }

  close(): void {
    this.closed.emit();
  }

  submit(): void {
    const name = this.name.trim();
    if (!name) {
      this.errorMessage = 'Informe o nome do insumo.';
      return;
    }

    const values = [this.availableQuantity, this.minimumQuantity, this.unitCost];
    if (values.some((value) => value.trim() && !this.isNonNegative(value))) {
      this.errorMessage = 'Quantidade e custo devem ser números maiores ou iguais a zero.';
      return;
    }

    this.submitted.emit({
      nome: name,
      quantidade_disponivel: this.toDecimalOrNull(this.availableQuantity),
      quantidade_minima: this.toDecimalOrNull(this.minimumQuantity),
      data_validade: this.expirationDate || null,
      custo_unitario: this.toDecimalOrNull(this.unitCost),
    });
  }

  private isNonNegative(value: string): boolean {
    const number = Number(this.toDecimalOrNull(value));
    return Number.isFinite(number) && number >= 0;
  }

  private toDecimalOrNull(value: string): string | null {
    const normalized = value.trim().replace(',', '.');
    return normalized ? normalized : null;
  }
}
