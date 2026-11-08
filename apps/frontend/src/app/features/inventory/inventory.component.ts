import { Component, inject, OnInit, signal } from '@angular/core';
import { MetricCardsComponent } from '../../shared/components/metric-cards/metric-cards.component';
import { MetricCardItem } from '../../shared/components/metric-cards/metric-cards.model';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';
import { Ingredient } from '../../core/models/api.model';
import { DomainApiService } from '../../core/services/domain-api.service';

interface InventoryItem {
  name: string;
  code: string;
  lot: string;
  level: string;
  percentage: number;
  unit: string;
  packaging: string;
  minimum: string;
  status: 'low' | 'normal' | 'critical';
  statusLabel: string;
  expiration: string;
  expirationDetail: string;
  cost: string;
  lastMovement: string;
  author: string;
}

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [PageGreetingComponent, MetricCardsComponent],
  templateUrl: './inventory.component.html',
  styleUrls: ['./inventory.component.scss'],
})
export class InventoryComponent implements OnInit {
  private readonly domainApi = inject(DomainApiService);
  private readonly ingredients = signal<Ingredient[]>([]);

  readonly loadError = signal<string | null>(null);

  readonly greetingActions: PageAction[] = [
    { label: 'Entrada / Saída Rápida', icon: 'filter', variant: 'secondary' },
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

  get inventoryItems(): InventoryItem[] {
    return this.ingredients().map((ingredient) => this.toInventoryItem(ingredient));
  }

  ngOnInit(): void {
    this.domainApi.getIngredients().subscribe({
      next: (ingredients) => {
        this.ingredients.set(ingredients);
        this.loadError.set(null);
      },
      error: (error: unknown) => {
        const detail = this.errorDetail(error);
        this.loadError.set(detail);
        console.error('Falha ao carregar o inventário de insumos.', error);
      },
    });
  }

  private toInventoryItem(ingredient: Ingredient): InventoryItem {
    const quantity = this.toNumber(ingredient.quantidade_disponivel);
    const minimum = this.toNumber(ingredient.quantidade_minima);
    const belowMinimum = ingredient.abaixo_do_minimo === true;
    const status =
      ingredient.quantidade_disponivel !== null && quantity <= 0
        ? 'critical'
        : belowMinimum
          ? 'low'
          : 'normal';

    return {
      name: ingredient.nome,
      code: `INS-${String(ingredient.id_ingrediente).padStart(4, '0')}`,
      lot: 'Lote não informado',
      level: `${this.formatQuantity(ingredient.quantidade_disponivel)} un.`,
      percentage:
        minimum > 0
          ? Math.min(100, Math.round((quantity / minimum) * 100))
          : quantity > 0
            ? 100
            : 0,
      unit: 'un.',
      packaging: 'Embalagem não informada',
      minimum:
        ingredient.quantidade_minima === null
          ? 'Não informado'
          : `${this.formatQuantity(ingredient.quantidade_minima)} un.`,
      status,
      statusLabel: status === 'critical' ? 'Esgotado' : status === 'low' ? 'Baixo' : 'Normal',
      expiration: this.formatDate(ingredient.data_validade),
      expirationDetail: this.expirationDetail(ingredient.alerta_validade),
      cost: this.formatCurrencyOrUnavailable(ingredient.custo_unitario),
      lastMovement: 'Não informado',
      author: 'Não informado',
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
