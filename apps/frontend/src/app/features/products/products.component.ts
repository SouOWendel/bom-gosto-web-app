import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  LucideDynamicIcon,
  LucidePackage,
  LucidePlus,
  LucidePencil,
  LucideSearch,
  LucideTrash2,
  provideLucideIcons,
} from '@lucide/angular';
import { DomainApiService } from '../../core/services/domain-api.service';
import { Product, Recipe } from '../../core/models/api.model';
import { apiErrorMessage } from '../../core/utils/api-error';
import { formatCurrency } from '../../core/utils/format';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';
import { MetricCardsComponent } from '../../shared/components/metric-cards/metric-cards.component';
import { MetricCardItem } from '../../shared/components/metric-cards/metric-cards.model';
import { ProductCreateModalComponent } from '../../shared/components/product-create-modal/product-create-modal.component';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-products',
  standalone: true,
  imports: [
    FormsModule,
    LucideDynamicIcon,
    PageGreetingComponent,
    MetricCardsComponent,
    ProductCreateModalComponent,
    ButtonComponent,
    ConfirmDialogComponent,
  ],
  providers: [
    provideLucideIcons(LucidePackage, LucidePlus, LucidePencil, LucideSearch, LucideTrash2),
  ],
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
  readonly productToDelete = signal<Product | null>(null);
  readonly isDeleting = signal(false);
  readonly deleteError = signal<string | null>(null);

  readonly greetingActions: PageAction[] = [
    { id: 'novo-produto', label: 'Novo produto', icon: 'plus', variant: 'primary' },
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
        value: formatCurrency(avgPrice),
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
    if (action.id === 'novo-produto') {
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

  openDeleteDialog(product: Product): void {
    this.deleteError.set(null);
    this.productToDelete.set(product);
  }

  closeDeleteDialog(): void {
    this.productToDelete.set(null);
    this.deleteError.set(null);
  }

  // Produtos com lotes ou pedidos são recusados pela API; a mensagem fica no diálogo.
  confirmDelete(): void {
    const product = this.productToDelete();
    if (!product) {
      return;
    }
    this.isDeleting.set(true);
    this.deleteError.set(null);
    this.domainApi.deleteProduct(product.id_produto).subscribe({
      next: () => {
        this.isDeleting.set(false);
        this.products.update((list) =>
          list.filter((item) => item.id_produto !== product.id_produto),
        );
        this.closeDeleteDialog();
      },
      error: (error: unknown) => {
        this.isDeleting.set(false);
        this.deleteError.set(apiErrorMessage(error));
      },
    });
  }

  formatPrice(price: string): string {
    const num = Number(price);
    return Number.isFinite(num) ? formatCurrency(num) : price;
  }
}
