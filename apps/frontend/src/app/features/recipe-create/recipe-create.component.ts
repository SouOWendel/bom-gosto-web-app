import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { InputTextComponent } from '../../shared/components/input-text/input-text.component';
import { ButtonComponent } from '../../shared/components/button/button.component';

interface RecipeIngredient {
  name: string;
  code: string;
  quantity: number;
  unit: string;
  unitCost: number;
}

@Component({
  selector: 'app-recipe-create',
  standalone: true,
  imports: [FormsModule, InputTextComponent, ButtonComponent],
  templateUrl: './recipe-create.component.html',
  styleUrls: ['./recipe-create.component.scss'],
})
export class RecipeCreateComponent {
  recipeName = 'Brownie de cacau';
  category = 'Doces & Sobremesas';
  product = 'Brownie de cacau 60 g · DOC-0032';
  yield = 20;
  yieldUnit = 'Unidade (un)';
  preparation =
    '1. Derreta o chocolate e a manteiga em banho-maria; deixe amornar.\n2. Misture os ovos com o açúcar. Incorpore o chocolate derretido.\n3. Peneire a farinha e o cacau; misture até a massa ficar homogênea.\n4. Distribua em forma de 20 × 30 cm forrada com papel-manteiga.\n5. Asse a 180 °C por 25 minutos. Espere esfriar completamente.\n6. Corte em 20 unidades de aproximadamente 60 g cada.';

  ingredients: RecipeIngredient[] = [
    { name: 'Chocolate meio amargo', code: 'INS-041', quantity: 400, unit: 'g', unitCost: 60 },
    { name: 'Manteiga sem sal', code: 'INS-042', quantity: 200, unit: 'g', unitCost: 40 },
    { name: 'Açúcar refinado', code: 'INS-043', quantity: 300, unit: 'g', unitCost: 6 },
    { name: 'Ovos', code: 'INS-044', quantity: 4, unit: 'un', unitCost: 1 },
    { name: 'Farinha de trigo', code: 'INS-045', quantity: 200, unit: 'g', unitCost: 6 },
    { name: 'Cacau em pó', code: 'INS-046', quantity: 100, unit: 'g', unitCost: 90 },
  ];

  get totalCost(): number {
    return this.ingredients.reduce((total, item) => {
      const divisor = item.unit === 'un' ? 1 : 1000;
      return total + (item.quantity / divisor) * item.unitCost;
    }, 0);
  }

  addIngredient(): void {
    this.ingredients = [
      ...this.ingredients,
      { name: 'Novo ingrediente', code: 'INS-000', quantity: 100, unit: 'g', unitCost: 0 },
    ];
  }

  removeIngredient(index: number): void {
    this.ingredients = this.ingredients.filter((_, itemIndex) => itemIndex !== index);
  }

  saveRecipe(): void {
    // A persistência será conectada ao serviço de receitas quando a API estiver disponível.
  }
}
