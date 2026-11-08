import { Component, OnInit, effect, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonComponent } from '../button/button.component';
import { InputTextComponent } from '../input-text/input-text.component';
import { Product, Recipe } from '../../../core/models/api.model';

@Component({
  selector: 'app-product-create-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, ButtonComponent, InputTextComponent],
  templateUrl: './product-create-modal.component.html',
  styleUrls: ['./product-create-modal.component.scss'],
})
export class ProductCreateModalComponent implements OnInit {
  readonly recipes = input<Recipe[]>([]);
  readonly productToEdit = input<Product | null>(null);
  readonly apiError = input<string | null>(null);
  readonly closed = output<void>();
  readonly submitted = output<Partial<Product>>();

  name = '';
  salePrice = '';
  recipeId: number | null = null;
  errorMessage = '';

  constructor() {
    effect(() => {
      const prod = this.productToEdit();
      if (prod) {
        this.name = prod.nome;
        this.salePrice = prod.preco_venda;
        this.recipeId = prod.receita ?? null;
      }
    });
  }

  ngOnInit(): void {
    const prod = this.productToEdit();
    if (prod) {
      this.name = prod.nome;
      this.salePrice = prod.preco_venda;
      this.recipeId = prod.receita ?? null;
    }
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

    const price = Number(this.salePrice.trim().replace(',', '.'));
    if (!Number.isFinite(price) || price < 0) {
      this.errorMessage = 'Informe um preço de venda válido (maior ou igual a zero).';
      return;
    }

    this.submitted.emit({
      nome: name,
      preco_venda: price.toFixed(2),
      receita: this.recipeId || null,
    });
  }
}
