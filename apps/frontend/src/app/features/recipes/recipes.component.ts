import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DomainApiService } from '../../core/services/domain-api.service';
import { Recipe as ApiRecipe } from '../../core/models/api.model';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { InputTextComponent } from '../../shared/components/input-text/input-text.component';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';

interface RecipeRow {
  id: number;
  name: string;
  code: string;
  ingredients: number;
  product: string;
  category: string;
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
export class RecipesComponent implements OnInit {
  private readonly api = inject(DomainApiService);

  readonly searchTerm = signal('');
  readonly selectedCategory = signal('Todas as receitas');
  readonly selectedUnit = signal('Todas as unidades');
  readonly recipes = signal<RecipeRow[]>([]);
  readonly errorMessage = signal('');
  readonly currentPage = signal(1);
  readonly pageSize = 6;

  readonly greetingActions: PageAction[] = [
    {
      label: 'Adicionar receita',
      route: '/receitas/nova-receita',
      icon: 'plus',
      variant: 'primary',
    },
  ];

  readonly categories = ['Todas as receitas'];

  readonly filteredRecipes = computed(() => {
    const search = this.searchTerm().trim().toLocaleLowerCase();
    const category = this.selectedCategory();
    const unit = this.selectedUnit();

    return this.recipes().filter((recipe) => {
      const matchesSearch =
        !search ||
        recipe.name.toLocaleLowerCase().includes(search) ||
        recipe.code.toLocaleLowerCase().includes(search) ||
        recipe.product.toLocaleLowerCase().includes(search);
      const matchesCategory = category === 'Todas as receitas';
      const matchesUnit =
        unit === 'Todas as unidades' ||
        recipe.unit === unit ||
        (unit === 'Unidade (un)' && recipe.unit === 'un') ||
        (unit === 'Quilograma (kg)' && recipe.unit === 'kg');
      return matchesSearch && matchesCategory && matchesUnit;
    });
  });

  readonly totalRecipes = computed(() => this.filteredRecipes().length);
  readonly paginatedRecipes = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize;
    return this.filteredRecipes().slice(start, start + this.pageSize);
  });
  readonly totalPages = computed(() => Math.ceil(this.totalRecipes() / this.pageSize));
  readonly pageNumbers = computed(() =>
    Array.from({ length: this.totalPages() }, (_, index) => index + 1),
  );
  readonly visibleRange = computed(() => {
    const total = this.totalRecipes();
    if (total === 0) {
      return { start: 0, end: 0 };
    }
    return {
      start: (this.currentPage() - 1) * this.pageSize + 1,
      end: Math.min(this.currentPage() * this.pageSize, total),
    };
  });

  ngOnInit(): void {
    this.api.getRecipes().subscribe({
      next: (recipes) => {
        this.recipes.set(recipes.map((recipe) => this.toRecipeRow(recipe)));
        this.errorMessage.set('');
        this.currentPage.set(1);
      },
      error: (error: unknown) => this.handleError(error),
    });
  }

  onSearch(value: string): void {
    this.searchTerm.set(value);
    this.currentPage.set(1);
  }

  onCategoryChange(category: string): void {
    this.selectedCategory.set(category);
    this.currentPage.set(1);
  }

  onUnitChange(unit: string): void {
    this.selectedUnit.set(unit);
    this.currentPage.set(1);
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
    }
  }

  formatCurrency(value: number): string {
    if (!Number.isFinite(value)) {
      return '—';
    }
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  private toRecipeRow(recipe: ApiRecipe): RecipeRow {
    const totalCost = Number(recipe.custo_calculado) || 0;
    const yieldQuantity = Number(recipe.rendimento_quantidade) || 0;
    const associatedProducts = recipe.produtos ?? [];
    const unit =
      associatedProducts.find((product) => product.unidade_medida)?.unidade_medida ?? '—';

    return {
      id: recipe.id_receita,
      name: recipe.nome,
      code: `#${recipe.id_receita}`,
      ingredients: recipe.ingredientes?.length ?? 0,
      product: associatedProducts.length
        ? associatedProducts.map((product) => `Produto #${product.produto}`).join(', ')
        : '—',
      category: '—',
      yield: recipe.rendimento_quantidade ?? '—',
      totalCost,
      unitCost: yieldQuantity > 0 ? totalCost / yieldQuantity : Number.NaN,
      unit,
    };
  }

  private handleError(error: unknown): void {
    const detail =
      error instanceof HttpErrorResponse
        ? this.extractErrorDetail(error.error) || error.message
        : 'Ocorreu um erro inesperado.';
    this.errorMessage.set(`Não foi possível carregar as receitas. ${detail}`);
    globalThis.alert(this.errorMessage());
  }

  private extractErrorDetail(error: unknown): string {
    if (typeof error === 'string') {
      return error;
    }
    if (error && typeof error === 'object') {
      return Object.entries(error)
        .map(
          ([field, messages]) =>
            `${field}: ${Array.isArray(messages) ? messages.join(', ') : String(messages)}`,
        )
        .join('; ');
    }
    return '';
  }
}
