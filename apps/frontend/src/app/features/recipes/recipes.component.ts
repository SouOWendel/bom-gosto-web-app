import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { forkJoin } from 'rxjs';
import { LucideDynamicIcon, LucidePlus, LucideSearch, provideLucideIcons } from '@lucide/angular';
import { DomainApiService } from '../../core/services/domain-api.service';
import { Product, Recipe as ApiRecipe } from '../../core/models/api.model';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';
import { TablePaginationComponent } from '../../shared/components/table-pagination/table-pagination.component';

interface RecipeRow {
  id: number;
  name: string;
  code: string;
  ingredients: number;
  product: string;
  yield: string;
  totalCost: number;
  unitCost: number;
}

@Component({
  selector: 'app-recipes',
  standalone: true,
  imports: [TablePaginationComponent, PageGreetingComponent, LucideDynamicIcon],
  providers: [provideLucideIcons(LucidePlus, LucideSearch)],
  templateUrl: './recipes.component.html',
  styleUrls: ['./recipes.component.scss'],
})
export class RecipesComponent implements OnInit {
  private readonly api = inject(DomainApiService);

  readonly searchTerm = signal('');
  readonly recipes = signal<RecipeRow[]>([]);
  readonly errorMessage = signal('');
  readonly currentPage = signal(1);
  readonly pageSize = 6;

  readonly greetingActions: PageAction[] = [
    {
      label: 'Nova receita',
      route: '/receitas/nova-receita',
      icon: 'plus',
      variant: 'primary',
    },
  ];

  readonly filteredRecipes = computed(() => {
    const search = this.searchTerm().trim().toLocaleLowerCase();
    return this.recipes().filter(
      (recipe) =>
        !search ||
        recipe.name.toLocaleLowerCase().includes(search) ||
        recipe.code.toLocaleLowerCase().includes(search) ||
        recipe.product.toLocaleLowerCase().includes(search),
    );
  });

  readonly totalRecipes = computed(() => this.filteredRecipes().length);
  readonly paginatedRecipes = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize;
    return this.filteredRecipes().slice(start, start + this.pageSize);
  });
  readonly totalPages = computed(() => Math.ceil(this.totalRecipes() / this.pageSize));

  ngOnInit(): void {
    forkJoin({ recipes: this.api.getRecipes(), products: this.api.getProducts() }).subscribe({
      next: ({ recipes, products }) => {
        this.recipes.set(recipes.map((recipe) => this.toRecipeRow(recipe, products)));
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

  // Produtos ligados pela receita principal (Produto.receita) ou por Receita_Produto.
  private toRecipeRow(recipe: ApiRecipe, products: Product[]): RecipeRow {
    const totalCost = Number(recipe.custo_calculado) || 0;
    const yieldQuantity = Number(recipe.rendimento_quantidade) || 0;
    const productIds = new Set([
      ...products
        .filter((product) => product.receita === recipe.id_receita)
        .map((p) => p.id_produto),
      ...(recipe.produtos ?? []).map((relation) => relation.produto),
    ]);
    const productNames = products
      .filter((product) => productIds.has(product.id_produto))
      .map((product) => product.nome);

    return {
      id: recipe.id_receita,
      name: recipe.nome,
      code: `#${recipe.id_receita}`,
      ingredients: recipe.ingredientes?.length ?? 0,
      product: productNames.join(', ') || 'Sem produto associado',
      yield:
        yieldQuantity > 0
          ? yieldQuantity.toLocaleString('pt-BR', { maximumFractionDigits: 2 })
          : 'Não informado',
      totalCost,
      unitCost: yieldQuantity > 0 ? totalCost / yieldQuantity : Number.NaN,
    };
  }

  private handleError(error: unknown): void {
    const detail =
      error instanceof HttpErrorResponse
        ? this.extractErrorDetail(error.error) || error.message
        : 'Ocorreu um erro inesperado.';
    this.errorMessage.set(`Não foi possível carregar as receitas. ${detail}`);
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
