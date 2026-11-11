import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import {
  LucideCheck,
  LucideDynamicIcon,
  LucidePlus,
  LucideTrash2,
  provideLucideIcons,
} from '@lucide/angular';
import {
  Ingredient,
  Product,
  Recipe as ApiRecipe,
  RecipeIngredient,
} from '../../core/models/api.model';
import { DomainApiService } from '../../core/services/domain-api.service';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { InputTextComponent } from '../../shared/components/input-text/input-text.component';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';

interface RecipeIngredientRow {
  id: number | null;
  name: string;
  code: string;
  quantity: number;
  unit: string;
  unitCost: number;
}

@Component({
  selector: 'app-recipe-create',
  standalone: true,
  imports: [
    FormsModule,
    InputTextComponent,
    ButtonComponent,
    PageGreetingComponent,
    LucideDynamicIcon,
  ],
  providers: [provideLucideIcons(LucideCheck, LucidePlus, LucideTrash2)],
  templateUrl: './recipe-create.component.html',
  styleUrls: ['./recipe-create.component.scss'],
})
export class RecipeCreateComponent implements OnInit {
  private readonly api = inject(DomainApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  recipeName = '';
  productId: number | null = null;
  yield = 0;
  preparation = '';
  ingredients: RecipeIngredientRow[] = [];
  errorMessage = '';
  isSaving = false;
  private recipeId: number | null = null;

  get isEditing(): boolean {
    return this.recipeId !== null;
  }
  availableIngredients: Ingredient[] = [];
  availableProducts: Product[] = [];

  readonly greetingActions: PageAction[] = [
    {
      label: 'Voltar para receitas',
      route: '/receitas',
      icon: 'arrow-left',
      variant: 'outline-primary',
    },
  ];

  // A quantidade é informada na mesma unidade do inventário, então o custo é direto.
  get totalCost(): number {
    return this.ingredients.reduce(
      (total, item) => total + (Number(item.quantity) || 0) * item.unitCost,
      0,
    );
  }

  get unitCost(): number {
    return this.yield > 0 ? this.totalCost / this.yield : 0;
  }

  formatCurrency(value: number): string {
    return (Number.isFinite(value) ? value : 0).toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    });
  }

  cancel(): void {
    void this.router.navigate(['/receitas']);
  }

  ngOnInit(): void {
    const rawId = this.route.snapshot.queryParamMap.get('id');
    if (rawId !== null) {
      const id = Number(rawId);
      if (!Number.isInteger(id) || id <= 0) {
        this.setError('O identificador da receita é inválido.');
        return;
      }
      this.recipeId = id;
    }

    this.api.getProducts().subscribe({
      next: (products) => (this.availableProducts = products),
      error: (err) => console.error('Erro ao carregar produtos', err),
    });

    if (this.recipeId === null) {
      this.api.getIngredients().subscribe({
        next: (ingredients) => {
          this.availableIngredients = ingredients;
        },
        error: (error: unknown) =>
          this.setError(`Não foi possível carregar os ingredientes. ${this.errorDetail(error)}`),
      });
      return;
    }

    forkJoin({
      recipes: this.api.getRecipes(),
      ingredients: this.api.getIngredients(),
    }).subscribe({
      next: ({ recipes, ingredients }) => {
        this.availableIngredients = ingredients;
        const recipe = recipes.find((item) => item.id_receita === this.recipeId);
        if (!recipe) {
          this.setError('A receita solicitada não foi encontrada.');
          return;
        }
        this.populateRecipe(recipe);
      },
      error: (error: unknown) =>
        this.setError(
          `Não foi possível carregar a receita ou os ingredientes. ${this.errorDetail(error)}`,
        ),
    });
  }

  addIngredient(): void {
    const ingredient = this.availableIngredients.find(
      (candidate) =>
        !this.ingredients.some(
          (item) => this.resolveIngredientId(item) === candidate.id_ingrediente,
        ),
    );
    this.ingredients = [
      ...this.ingredients,
      {
        id: ingredient?.id_ingrediente ?? null,
        name: ingredient?.nome ?? '',
        code: ingredient ? String(ingredient.id_ingrediente) : '',
        quantity: 1,
        unit: ingredient?.unidade_medida ?? 'un',
        unitCost: Number(ingredient?.custo_unitario) || 0,
      },
    ];
  }

  removeIngredient(index: number): void {
    this.ingredients = this.ingredients.filter((_, itemIndex) => itemIndex !== index);
  }

  onIngredientSelected(index: number, ingredientId: number | null): void {
    const ingredient = this.availableIngredients.find(
      (candidate) => candidate.id_ingrediente === ingredientId,
    );
    this.ingredients = this.ingredients.map((item, itemIndex) =>
      itemIndex === index
        ? {
            ...item,
            id: ingredientId,
            name: ingredient?.nome ?? '',
            code: ingredient ? String(ingredient.id_ingrediente) : '',
            unit: ingredient?.unidade_medida ?? 'un',
            unitCost: Number(ingredient?.custo_unitario) || 0,
          }
        : item,
    );
  }

  saveRecipe(): void {
    const validationError = this.validateRecipe();
    if (validationError) {
      this.setError(validationError);
      return;
    }

    const payload: Partial<ApiRecipe> & { ingredientes: RecipeIngredient[] } = {
      nome: this.recipeName.trim(),
      rendimento_quantidade: String(this.yield),
      ingredientes: this.ingredients.map((item) => ({
        ingrediente: this.resolveIngredientId(item) as number,
        quantidade_necessaria: String(item.quantity),
      })),
    };

    this.isSaving = true;
    this.errorMessage = '';
    const request =
      this.recipeId === null
        ? this.api.createRecipe(payload)
        : this.api.updateRecipe(this.recipeId, payload);
    request.subscribe({
      next: (savedRecipe) => {
        if (this.productId) {
          this.api.updateProduct(this.productId, { receita: savedRecipe.id_receita }).subscribe({
            next: () => {
              this.isSaving = false;
              void this.router.navigate(['/receitas']);
            },
            error: () => {
              this.isSaving = false;
              void this.router.navigate(['/receitas']);
            },
          });
        } else {
          this.isSaving = false;
          void this.router.navigate(['/receitas']);
        }
      },
      error: (error: unknown) => {
        this.isSaving = false;
        this.setError(`Não foi possível salvar a receita. ${this.errorDetail(error)}`);
      },
    });
  }

  private populateRecipe(recipe: ApiRecipe): void {
    this.recipeName = recipe.nome;
    this.yield = Number(recipe.rendimento_quantidade) || 0;
    this.ingredients = (recipe.ingredientes ?? []).map((item) => {
      const ingredient = this.availableIngredients.find(
        (available) => available.id_ingrediente === item.ingrediente,
      );
      return {
        id: item.ingrediente,
        name: ingredient?.nome ?? `Ingrediente #${item.ingrediente}`,
        code: String(item.ingrediente),
        quantity: Number(item.quantidade_necessaria) || 0,
        unit: ingredient?.unidade_medida ?? 'un',
        unitCost: Number(ingredient?.custo_unitario) || 0,
      };
    });
  }

  private validateRecipe(): string | null {
    if (!this.recipeName.trim()) {
      return 'Informe o nome da receita.';
    }
    if (!Number.isFinite(this.yield) || this.yield <= 0) {
      return 'O rendimento deve ser maior que zero.';
    }
    if (this.ingredients.some((item) => this.resolveIngredientId(item) === null)) {
      return 'Selecione ingredientes cadastrados no inventário.';
    }
    if (this.ingredients.some((item) => !Number.isFinite(item.quantity) || item.quantity <= 0)) {
      return 'A quantidade de cada ingrediente deve ser maior que zero.';
    }
    const ids = this.ingredients.map((item) => this.resolveIngredientId(item));
    if (new Set(ids).size !== ids.length) {
      return 'Cada ingrediente pode aparecer uma única vez na receita.';
    }
    return null;
  }

  private resolveIngredientId(item: RecipeIngredientRow): number | null {
    return item.id;
  }

  private setError(detail: string): void {
    this.errorMessage = detail;
  }

  private errorDetail(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const body = error.error;
      if (typeof body === 'string') {
        return body;
      }
      if (body && typeof body === 'object') {
        return Object.entries(body)
          .map(
            ([field, messages]) =>
              `${field}: ${Array.isArray(messages) ? messages.join(', ') : String(messages)}`,
          )
          .join('; ');
      }
      return error.message;
    }
    return 'Ocorreu um erro inesperado.';
  }
}
