import { Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { InputTextComponent } from '../../shared/components/input-text/input-text.component';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';

interface Recipe {
  name: string;
  code: string;
  ingredients: number;
  product: string;
  category: 'Bolos' | 'Doces e brigadeiros' | 'Massas e recheios';
  yield: string;
  totalCost: number;
  unitCost: number;
  unit: string;
}

@Component({
  selector: 'app-recipes',
  standalone: true,
  imports: [FormsModule, ButtonComponent, InputTextComponent, PageGreetingComponent],
  templateUrl: './recipes.component.html',
  styleUrls: ['./recipes.component.scss'],
})
export class RecipesComponent {
  readonly searchTerm = signal('');
  readonly selectedCategory = signal('Todas as receitas');
  readonly selectedUnit = signal('Todas as unidades');

  readonly greetingActions: PageAction[] = [
    {
      label: 'Cadastrar nova receita',
      route: '/receitas/nova-receita',
      icon: 'plus',
      variant: 'primary',
    },
  ];

  readonly categories = ['Todas as receitas', 'Bolos', 'Doces e brigadeiros', 'Massas e recheios'];

  readonly recipes: Recipe[] = [
    {
      name: 'Brigadeiro tradicional',
      code: 'REC-001',
      ingredients: 4,
      product: 'Brigadeiro tradicional 20 g',
      category: 'Doces e brigadeiros',
      yield: '40 unidades',
      totalCost: 32,
      unitCost: 0.8,
      unit: 'unidade',
    },
    {
      name: 'Bolo de cenoura',
      code: 'REC-002',
      ingredients: 8,
      product: 'Bolo de cenoura com chocolate',
      category: 'Bolos',
      yield: '2 kg',
      totalCost: 48,
      unitCost: 24,
      unit: 'kg',
    },
    {
      name: 'Beijinho de coco',
      code: 'REC-003',
      ingredients: 5,
      product: 'Beijinho de coco 20 g',
      category: 'Doces e brigadeiros',
      yield: '50 unidades',
      totalCost: 35,
      unitCost: 0.7,
      unit: 'unidade',
    },
    {
      name: 'Ganache meio amargo',
      code: 'REC-004',
      ingredients: 2,
      product: 'Recheio de ganache meio amargo',
      category: 'Massas e recheios',
      yield: '1.000 gramas',
      totalCost: 45,
      unitCost: 0.045,
      unit: 'grama',
    },
    {
      name: 'Brownie de chocolate',
      code: 'REC-005',
      ingredients: 7,
      product: 'Brownie de chocolate 60 g',
      category: 'Doces e brigadeiros',
      yield: '24 unidades',
      totalCost: 57.6,
      unitCost: 2.4,
      unit: 'unidade',
    },
    {
      name: 'Massa de pão de ló',
      code: 'REC-006',
      ingredients: 4,
      product: 'Base de pão de ló de baunilha',
      category: 'Massas e recheios',
      yield: '1,5 kg',
      totalCost: 27,
      unitCost: 18,
      unit: 'kg',
    },
  ];

  readonly filteredRecipes = computed(() => {
    const search = this.searchTerm().trim().toLocaleLowerCase();
    const category = this.selectedCategory();

    return this.recipes.filter((recipe) => {
      const matchesSearch =
        !search ||
        recipe.name.toLocaleLowerCase().includes(search) ||
        recipe.code.toLocaleLowerCase().includes(search) ||
        recipe.product.toLocaleLowerCase().includes(search);
      const matchesCategory = category === 'Todas as receitas' || recipe.category === category;
      return matchesSearch && matchesCategory;
    });
  });

  readonly totalRecipes = computed(() => this.filteredRecipes().length);

  onSearch(value: string): void {
    this.searchTerm.set(value);
  }

  onCategoryChange(category: string): void {
    this.selectedCategory.set(category);
  }

  formatCurrency(value: number): string {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }
}
