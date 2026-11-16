import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
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
import { apiErrorMessage } from '../../core/utils/api-error';
import { formatCurrency, parseDecimal } from '../../core/utils/format';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { InputTextComponent } from '../../shared/components/input-text/input-text.component';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';

interface RecipeIngredientRow {
  id: number | null;
  name: string;
  code: string;
  // Texto digitado no campo (o input compartilhado emite string); converta com parseDecimal.
  quantity: string;
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
  // O app é zoneless: respostas assíncronas da API precisam pedir nova renderização.
  private readonly cdr = inject(ChangeDetectorRef);

  recipeName = '';
  // Texto digitado no campo (o input compartilhado emite string); use yieldValue para cálculos.
  yield = '';
  ingredients: RecipeIngredientRow[] = [];
  errorMessage = '';
  isSaving = false;
  private recipeId: number | null = null;

  get isEditing(): boolean {
    return this.recipeId !== null;
  }

  // Produtos que usam esta receita. O vínculo é feito no cadastro de produtos (RF18):
  // como principal (Produto.receita) ou como complementar (Receita_Produto).
  get usedInProducts(): string[] {
    if (this.recipeId === null) {
      return [];
    }
    const id = this.recipeId;
    return this.availableProducts.flatMap((product) => {
      if (product.receita === id) {
        return [`${product.nome} (principal)`];
      }
      if ((product.receitas_complementares ?? []).some((item) => item.receita === id)) {
        return [`${product.nome} (complementar)`];
      }
      return [];
    });
  }
  availableIngredients: Ingredient[] = [];
  availableProducts: Product[] = [];

  readonly greetingActions: PageAction[] = [
    {
      label: 'Voltar para receitas',
      route: '/receitas',
      icon: 'arrow-left',
      variant: 'outline',
    },
  ];

  // A quantidade é informada na mesma unidade do inventário, então o custo é direto.
  get totalCost(): number {
    return this.ingredients.reduce((total, item) => total + this.lineCost(item), 0);
  }

  // Custo da linha: quantidade digitada (texto) vezes o custo unitário do insumo.
  lineCost(item: RecipeIngredientRow): number {
    const quantity = Number(parseDecimal(String(item.quantity ?? '')));
    return (Number.isFinite(quantity) ? quantity : 0) * item.unitCost;
  }

  get yieldValue(): number {
    const value = Number(parseDecimal(String(this.yield ?? '')));
    return Number.isFinite(value) ? value : 0;
  }

  get unitCost(): number {
    return this.yieldValue > 0 ? this.totalCost / this.yieldValue : 0;
  }

  readonly formatCurrency = formatCurrency;

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
      next: (products) => {
        this.availableProducts = products;
        this.cdr.markForCheck();
      },
      error: (err) => console.error('Erro ao carregar produtos', err),
    });

    if (this.recipeId === null) {
      this.api.getIngredients().subscribe({
        next: (ingredients) => {
          this.availableIngredients = ingredients;
          this.cdr.markForCheck();
        },
        error: (error: unknown) =>
          this.setError(`Não foi possível carregar os ingredientes. ${apiErrorMessage(error)}`),
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
        this.cdr.markForCheck();
      },
      error: (error: unknown) =>
        this.setError(
          `Não foi possível carregar a receita ou os ingredientes. ${apiErrorMessage(error)}`,
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
        quantity: '1',
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
      rendimento_quantidade: String(this.yieldValue),
      ingredientes: this.ingredients.map((item) => ({
        ingrediente: this.resolveIngredientId(item) as number,
        quantidade_necessaria: parseDecimal(item.quantity),
      })),
    };

    this.isSaving = true;
    this.errorMessage = '';
    const request =
      this.recipeId === null
        ? this.api.createRecipe(payload)
        : this.api.updateRecipe(this.recipeId, payload);
    request.subscribe({
      next: () => {
        this.isSaving = false;
        void this.router.navigate(['/receitas']);
      },
      error: (error: unknown) => {
        this.isSaving = false;
        this.setError(`Não foi possível salvar a receita. ${apiErrorMessage(error)}`);
      },
    });
  }

  private populateRecipe(recipe: ApiRecipe): void {
    this.recipeName = recipe.nome;
    this.yield = String(Number(recipe.rendimento_quantidade) || '');
    this.ingredients = (recipe.ingredientes ?? []).map((item) => {
      const ingredient = this.availableIngredients.find(
        (available) => available.id_ingrediente === item.ingrediente,
      );
      return {
        id: item.ingrediente,
        name: ingredient?.nome ?? `Ingrediente #${item.ingrediente}`,
        code: String(item.ingrediente),
        quantity: String(Number(item.quantidade_necessaria) || ''),
        unit: ingredient?.unidade_medida ?? 'un',
        unitCost: Number(ingredient?.custo_unitario) || 0,
      };
    });
  }

  private validateRecipe(): string | null {
    if (!this.recipeName.trim()) {
      return 'Informe o nome da receita.';
    }
    if (this.yieldValue <= 0) {
      return 'O rendimento deve ser maior que zero.';
    }
    if (this.ingredients.some((item) => this.resolveIngredientId(item) === null)) {
      return 'Selecione ingredientes cadastrados no inventário.';
    }
    // A API guarda a quantidade com até 2 casas decimais (IngredienteReceita).
    if (
      this.ingredients.some((item) => {
        const quantity = parseDecimal(String(item.quantity ?? ''));
        return !/^\d+(\.\d{1,2})?$/.test(quantity) || Number(quantity) <= 0;
      })
    ) {
      return 'A quantidade de cada ingrediente deve ser maior que zero e ter até 2 casas decimais.';
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
    this.cdr.markForCheck();
  }
}
