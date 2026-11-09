import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { LucideDynamicIcon, LucidePencil, provideLucideIcons } from '@lucide/angular';
import { MetricCardsComponent } from '../../shared/components/metric-cards/metric-cards.component';
import { MetricCardItem } from '../../shared/components/metric-cards/metric-cards.model';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';
import { Ingredient } from '../../core/models/api.model';
import { DomainApiService } from '../../core/services/domain-api.service';
import {
  IngredientCreateModalComponent,
  IngredientCreationPayload,
} from '../../shared/components/ingredient-create-modal/ingredient-create-modal.component';
import { TablePaginationComponent } from '../../shared/components/table-pagination/table-pagination.component';

interface InventoryItem {
  raw: Ingredient;
  name: string;
  code: string;
  lot: string;
  level: string;
  percentage: number;
  unit: string;
  minimum: string;
  status: 'low' | 'normal' | 'critical';
  statusLabel: string;
  expiration: string;
  expirationDetail: string;
  expirationLevel: 'critico' | 'atencao' | 'preventivo' | null;
  expirationLabel: string;
  cost: string;
}

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [
    TablePaginationComponent,
    PageGreetingComponent,
    MetricCardsComponent,
    IngredientCreateModalComponent,
    LucideDynamicIcon,
  ],
  providers: [provideLucideIcons(LucidePencil)],
  templateUrl: './inventory.component.html',
  styleUrls: ['./inventory.component.scss'],
})
export class InventoryComponent implements OnInit {
  private readonly domainApi = inject(DomainApiService);
  readonly ingredients = signal<Ingredient[]>([]);

  readonly loadError = signal<string | null>(null);
  readonly isCreateModalOpen = signal(false);
  readonly createError = signal<string | null>(null);
  readonly ingredientToEdit = signal<Ingredient | null>(null);
  readonly searchTerm = signal('');
  readonly alertOnly = signal(false);
  readonly currentPage = signal(1);
  readonly pageSize = 5;
  readonly totalItems = computed(() => this.filteredInventoryItems().length);
  readonly paginatedInventoryItems = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize;
    return this.filteredInventoryItems().slice(start, start + this.pageSize);
  });
  readonly totalPages = computed(() => Math.ceil(this.totalItems() / this.pageSize));

  readonly greetingActions: PageAction[] = [
    { label: 'Novo Insumo', icon: 'plus', variant: 'primary' },
  ];

  get summaryCards(): MetricCardItem[] {
    const ingredients = this.ingredients();
    const belowMinimum = ingredients.filter(
      (ingredient) => ingredient.abaixo_do_minimo === true,
    ).length;
    const exhausted = ingredients.filter(
      (ingredient) =>
        ingredient.quantidade_disponivel !== null &&
        this.toNumber(ingredient.quantidade_disponivel) <= 0,
    ).length;
    const totalValue = ingredients.reduce(
      (total, ingredient) =>
        total +
        this.toNumber(ingredient.quantidade_disponivel) * this.toNumber(ingredient.custo_unitario),
      0,
    );

    return [
      {
        label: 'Total de itens',
        value: String(ingredients.length),
        subtext: 'Insumos cadastrados',
        icon: 'package',
        variant: 'destaque',
      },
      {
        label: 'Valor em estoque',
        value: this.formatCurrency(totalValue),
        subtext: 'Estimado por quantidade e custo unitário',
        icon: 'banknote',
        variant: 'neutro',
      },
      {
        label: 'Estoque baixo',
        value: String(belowMinimum),
        subtext: 'Abaixo da quantidade mínima',
        icon: 'circle-alert',
        variant: 'alerta',
      },
      {
        label: 'Itens esgotados',
        value: String(exhausted),
        subtext: 'Sem quantidade disponível',
        icon: 'shopping-bag',
        variant: 'neutro',
      },
    ];
  }

  get totalAlertsCount(): number {
    return this.ingredients().filter(
      (item) => item.abaixo_do_minimo || item.alerta_validade !== null,
    ).length;
  }

  readonly filteredInventoryItems = computed(() => {
    const term = this.searchTerm().trim().toLowerCase();
    const alertFilter = this.alertOnly();

    return this.ingredients()
      .filter((item) => {
        if (alertFilter && !item.abaixo_do_minimo && !item.alerta_validade) {
          return false;
        }
        if (!term) return true;
        return item.nome.toLowerCase().includes(term) || String(item.id_ingrediente).includes(term);
      })
      .map((item) => this.toInventoryItem(item));
  });

  toggleAlertFilter(): void {
    this.alertOnly.update((v) => !v);
  }

  ngOnInit(): void {
    this.domainApi.getIngredients().subscribe({
      next: (ingredients) => {
        this.ingredients.set(ingredients);
        this.loadError.set(null);
        this.currentPage.set(1);
      },
      error: (error: unknown) => {
        const detail = this.errorDetail(error);
        this.loadError.set(detail);
        console.error('Falha ao carregar o inventário de insumos.', error);
      },
    });
  }

  onSearch(value: string): void {
    this.searchTerm.set(value);
    this.currentPage.set(1);
  }

  setAlertFilter(value: boolean): void {
    this.alertOnly.set(value);
    this.currentPage.set(1);
  }

  handleGreetingAction(action: PageAction): void {
    if (action.label === 'Novo Insumo') {
      this.openCreateModal();
    }
  }

  openCreateModal(): void {
    this.ingredientToEdit.set(null);
    this.createError.set(null);
    this.isCreateModalOpen.set(true);
  }

  openEditModal(item: InventoryItem): void {
    this.ingredientToEdit.set(item.raw);
    this.createError.set(null);
    this.isCreateModalOpen.set(true);
  }

  closeCreateModal(): void {
    this.isCreateModalOpen.set(false);
    this.ingredientToEdit.set(null);
    this.createError.set(null);
  }

  saveIngredient(payload: IngredientCreationPayload): void {
    const toEdit = this.ingredientToEdit();
    if (toEdit) {
      this.domainApi.updateIngredient(toEdit.id_ingrediente, payload).subscribe({
        next: (updated) => {
          this.ingredients.update((items) =>
            items.map((it) => (it.id_ingrediente === updated.id_ingrediente ? updated : it)),
          );
          this.closeCreateModal();
        },
        error: (error: unknown) => {
          this.createError.set(`Não foi possível atualizar o insumo. ${this.errorDetail(error)}`);
          console.error('Falha ao atualizar insumo.', error);
        },
      });
    } else {
      this.domainApi.createIngredient(payload).subscribe({
        next: (ingredient) => {
          this.ingredients.update((items) => [...items, ingredient]);
          this.closeCreateModal();
        },
        error: (error: unknown) => {
          this.createError.set(`Não foi possível cadastrar o insumo. ${this.errorDetail(error)}`);
          console.error('Falha ao cadastrar insumo.', error);
        },
      });
    }
  }

  goToPage(page: number): void {
    if (page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
    }
  }

  private toInventoryItem(ingredient: Ingredient): InventoryItem {
    const quantity = this.toNumber(ingredient.quantidade_disponivel);
    const minimum = this.toNumber(ingredient.quantidade_minima);
    const belowMinimum = ingredient.abaixo_do_minimo === true;
    const unit = ingredient.unidade_medida || 'un';
    const status =
      ingredient.quantidade_disponivel !== null && quantity <= 0
        ? 'critical'
        : belowMinimum
          ? 'low'
          : 'normal';

    return {
      raw: ingredient,
      name: ingredient.nome,
      code: `INS-${String(ingredient.id_ingrediente).padStart(4, '0')}`,
      lot: '',
      level: `${this.formatQuantity(ingredient.quantidade_disponivel)} ${unit}`,
      percentage:
        minimum > 0
          ? Math.min(100, Math.round((quantity / minimum) * 100))
          : quantity > 0
            ? 100
            : 0,
      unit,
      minimum:
        ingredient.quantidade_minima === null
          ? 'Não informado'
          : `${this.formatQuantity(ingredient.quantidade_minima)} ${unit}`,
      status,
      statusLabel: status === 'critical' ? 'Esgotado' : status === 'low' ? 'Baixo' : 'Normal',
      expiration: this.formatDate(ingredient.data_validade),
      expirationDetail: this.expirationDetail(ingredient.alerta_validade),
      expirationLevel: ingredient.alerta_validade?.nivel ?? null,
      expirationLabel: this.expirationLabel(ingredient.alerta_validade?.nivel ?? null),
      cost: this.formatCurrencyOrUnavailable(ingredient.custo_unitario),
    };
  }

  private toNumber(value: string | null): number {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  private formatQuantity(value: string | null): string {
    return value === null
      ? 'Não informado'
      : this.toNumber(value).toLocaleString('pt-BR', { maximumFractionDigits: 2 });
  }

  private formatCurrency(value: number): string {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  private formatCurrencyOrUnavailable(value: string | null): string {
    return value === null ? 'Não informado' : this.formatCurrency(this.toNumber(value));
  }

  private formatDate(value: string | null): string {
    if (value === null) {
      return 'Não informada';
    }

    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('pt-BR');
  }

  // Semáforo de validade (RN17): crítico, atenção ou preventivo.
  private expirationLabel(level: InventoryItem['expirationLevel']): string {
    switch (level) {
      case 'critico':
        return 'Crítico';
      case 'atencao':
        return 'Atenção';
      case 'preventivo':
        return 'Preventivo';
      default:
        return '';
    }
  }

  private expirationDetail(alert: Ingredient['alerta_validade']): string {
    if (alert === null) {
      return 'Sem alerta';
    }

    if (alert.dias_para_vencer < 0) {
      return `Vencido há ${Math.abs(alert.dias_para_vencer)} dia(s)`;
    }

    if (alert.dias_para_vencer === 0) {
      return 'Vence hoje';
    }

    return `Vence em ${alert.dias_para_vencer} dia(s)`;
  }

  private errorDetail(error: unknown): string {
    return error instanceof Error ? error.message : 'Erro desconhecido ao consultar a API.';
  }
}
