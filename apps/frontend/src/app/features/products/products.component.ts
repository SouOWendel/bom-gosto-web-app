import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  LucideDynamicIcon,
  LucidePackage,
  LucidePlus,
  LucidePencil,
  LucideSearch,
  provideLucideIcons,
} from '@lucide/angular';
import { DomainApiService } from '../../core/services/domain-api.service';
import { Product, Recipe } from '../../core/models/api.model';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';
import { MetricCardsComponent } from '../../shared/components/metric-cards/metric-cards.component';
import { MetricCardItem } from '../../shared/components/metric-cards/metric-cards.model';
import { ProductCreateModalComponent } from '../../shared/components/product-create-modal/product-create-modal.component';

@Component({
  selector: 'app-products',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideDynamicIcon,
    PageGreetingComponent,
    MetricCardsComponent,
    ProductCreateModalComponent,
  ],
  providers: [provideLucideIcons(LucidePackage, LucidePlus, LucidePencil, LucideSearch)],
  templateUrl: './products.component.html',
  styleUrls: ['./products.component.scss'],
})
export class ProductsComponent implements OnInit {
  private readonly domainApi = inject(DomainApiService);

  readonly products = signal<Product[]>([]);
  readonly recipes = signal<Recipe[]>([]);
  readonly isModalOpen = signal(false);
  readonly productToEdit = signal<Product | null>(null);
  readonly apiError = signal<string | null>(null);
  readonly searchTerm = signal('');

  readonly greetingActions: PageAction[] = [
    { label: '+ Novo Produto', icon: 'plus', variant: 'primary' },
  ];

  get summaryCards(): MetricCardItem[] {
    const list = this.products();
    const avgPrice = list.length
      ? list.reduce((acc, p) => acc + (Number(p.preco_venda) || 0), 0) / list.length
      : 0;

    return [
      {
        label: 'Total de produtos',
        value: `${list.length} itens`,
        subtext: 'Cadastrados no catálogo',
        icon: 'package',
        variant: 'destaque',
      },
      {
        label: 'Preço médio de venda',
        value: this.formatCurrency(avgPrice),
        subtext: 'Média do catálogo ativo',
        icon: 'banknote',
        variant: 'pedidos',
      },
    ];
  }

  readonly filteredProducts = computed(() => {
    const term = this.searchTerm().trim().toLowerCase();
    return this.products().filter((p) => {
      if (!term) return true;
      return (
        p.nome.toLowerCase().includes(term) ||
        String(p.id_produto).includes(term) ||
        (p.receita_nome && p.receita_nome.toLowerCase().includes(term))
      );
    });
  });

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.domainApi.getProducts().subscribe({
      next: (prods) => this.products.set(prods),
      error: (err) => console.error('Erro ao carregar produtos', err),
    });

    this.domainApi.getRecipes().subscribe({
      next: (recs) => this.recipes.set(recs),
      error: (err) => console.error('Erro ao carregar receitas', err),
    });
  }

  handleGreetingAction(action: PageAction): void {
    if (action.label === '+ Novo Produto') {
      this.openCreateModal();
    }
  }

  openCreateModal(): void {
    this.productToEdit.set(null);
    this.apiError.set(null);
    this.isModalOpen.set(true);
  }

  openEditModal(product: Product): void {
    this.productToEdit.set(product);
    this.apiError.set(null);
    this.isModalOpen.set(true);
  }

  closeModal(): void {
    this.isModalOpen.set(false);
    this.productToEdit.set(null);
    this.apiError.set(null);
  }

  handleProductSubmit(payload: Partial<Product>): void {
    const toEdit = this.productToEdit();
    if (toEdit) {
      this.domainApi.updateProduct(toEdit.id_produto, payload).subscribe({
        next: (updated) => {
          this.products.update((list) =>
            list.map((item) => (item.id_produto === updated.id_produto ? updated : item)),
          );
          this.closeModal();
        },
        error: (err) => {
          this.apiError.set('Falha ao atualizar o produto. Verifique os dados.');
          console.error(err);
        },
      });
    } else {
      this.domainApi.createProduct(payload).subscribe({
        next: (created) => {
          this.products.update((list) => [...list, created]);
          this.closeModal();
        },
        error: (err) => {
          this.apiError.set('Falha ao cadastrar o produto. Verifique os dados.');
          console.error(err);
        },
      });
    }
  }

  formatCurrency(value: number): string {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  formatPrice(price: string): string {
    const num = Number(price);
    return Number.isFinite(num) ? this.formatCurrency(num) : price;
  }
}
