import { Component, HostListener, effect, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  LucideDynamicIcon,
  LucidePlus,
  LucideTrash2,
  LucideX,
  provideLucideIcons,
} from '@lucide/angular';
import { ButtonComponent } from '../button/button.component';
import { InputTextComponent } from '../input-text/input-text.component';
import { Product, Recipe } from '../../../core/models/api.model';
import { formatQuantity, parseDecimal, toDisplayDecimal } from '../../../core/utils/format';

interface ComplementaryRecipeRow {
  recipeId: number | null;
  quantity: string;
  unit: string;
}

@Component({
  selector: 'app-product-create-modal',
  standalone: true,
  imports: [FormsModule, ButtonComponent, InputTextComponent, LucideDynamicIcon],
  providers: [provideLucideIcons(LucidePlus, LucideTrash2, LucideX)],
  templateUrl: './product-create-modal.component.html',
  styleUrls: ['./product-create-modal.component.scss'],
})
export class ProductCreateModalComponent {
  readonly recipes = input<Recipe[]>([]);
  readonly productToEdit = input<Product | null>(null);
  readonly apiError = input<string | null>(null);
  readonly closed = output<void>();
  readonly submitted = output<Partial<Product>>();

  readonly units = ['un', 'kg', 'g', 'L', 'ml'];

  name = '';
  salePrice = '';
  recipeId: number | null = null;
  complementary: ComplementaryRecipeRow[] = [];
  errorMessage = '';

  constructor() {
    effect(() => {
      const prod = this.productToEdit();
      if (prod) {
        this.name = prod.nome;
        this.salePrice = prod.preco_venda;
        this.recipeId = prod.receita ?? null;
        this.complementary = (prod.receitas_complementares ?? []).map((item) => ({
          recipeId: item.receita,
          quantity: toDisplayDecimal(item.quantidade),
          unit: item.unidade_medida ?? 'un',
        }));
      }
    });
  }

  // Mostra quanto a receita rende para orientar a quantidade usada por produto.
  yieldHint(recipeId: number | null): string {
    const recipe = this.recipes().find((item) => item.id_receita === recipeId);
    if (!recipe?.rendimento_quantidade) {
      return '';
    }
    return `A receita rende ${formatQuantity(recipe.rendimento_quantidade)}; informe na mesma unidade.`;
  }

  addComplementary(): void {
    this.complementary = [...this.complementary, { recipeId: null, quantity: '', unit: 'kg' }];
  }

  removeComplementary(index: number): void {
    this.complementary = this.complementary.filter((_, itemIndex) => itemIndex !== index);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  close(): void {
    this.closed.emit();
  }

  submit(): void {
    const name = this.name.trim();
    if (!name) {
      this.errorMessage = 'Informe o nome do produto.';
      return;
    }

    const price = Number(parseDecimal(this.salePrice));
    if (!Number.isFinite(price) || price < 0) {
      this.errorMessage = 'Informe um preço de venda válido (maior ou igual a zero).';
      return;
    }

    const complementaryError = this.validateComplementary();
    if (complementaryError) {
      this.errorMessage = complementaryError;
      return;
    }

    this.errorMessage = '';
    this.submitted.emit({
      nome: name,
      preco_venda: price.toFixed(2),
      receita: this.recipeId || null,
      receitas_complementares: this.complementary.map((item) => ({
        receita: item.recipeId as number,
        quantidade: parseDecimal(item.quantity),
        unidade_medida: item.unit,
      })),
    });
  }

  private validateComplementary(): string | null {
    if (this.complementary.some((item) => item.recipeId === null)) {
      return 'Selecione a receita de cada linha complementar ou remova a linha.';
    }
    // A API guarda a quantidade com até 3 casas decimais (Receita_Produto.quantidade).
    if (
      this.complementary.some((item) => {
        const quantity = parseDecimal(item.quantity);
        return !/^\d+(\.\d{1,3})?$/.test(quantity) || Number(quantity) <= 0;
      })
    ) {
      return 'Informe a quantidade de cada receita complementar, maior que zero e com até 3 casas decimais.';
    }
    const ids = this.complementary.map((item) => item.recipeId);
    if (new Set(ids).size !== ids.length) {
      return 'Cada receita pode aparecer uma vez no produto.';
    }
    if (this.recipeId !== null && ids.includes(this.recipeId)) {
      return 'A receita principal não pode ser repetida como complementar.';
    }
    return null;
  }
}
