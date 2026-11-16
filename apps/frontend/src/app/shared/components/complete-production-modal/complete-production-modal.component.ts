import { Component, HostListener, input, OnInit, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LucideCheck, LucideDynamicIcon, LucideX, provideLucideIcons } from '@lucide/angular';
import { InputTextComponent } from '../input-text/input-text.component';
import { ButtonComponent } from '../button/button.component';
import {
  CompleteProductionPayload,
  ProductionAnalysis,
  ProductionConsumption,
} from '../../../core/models/api.model';
import { formatQuantity } from '../../../core/utils/format';

interface ProductionIngredient {
  // Chave da linha: o mesmo ingrediente pode aparecer em mais de uma receita.
  key: string;
  id: number;
  name: string;
  lot: string;
  theoreticalQuantity: string;
  theoreticalLabel: string;
  quantity: string;
  availableQuantity: string;
  unit: string;
}

interface ProductionGroup {
  recipeName: string | null;
  ingredients: ProductionIngredient[];
}

interface ProductionOrder {
  id: string;
  item: string;
  analysis: ProductionAnalysis | null;
}

@Component({
  selector: 'app-complete-production-modal',
  standalone: true,
  imports: [FormsModule, InputTextComponent, ButtonComponent, LucideDynamicIcon],
  providers: [provideLucideIcons(LucideCheck, LucideX)],
  templateUrl: './complete-production-modal.component.html',
  styleUrls: ['./complete-production-modal.component.scss'],
})
export class CompleteProductionModalComponent implements OnInit {
  readonly order = input.required<ProductionOrder>();
  readonly apiError = input<string | null>(null);
  readonly closed = output<void>();
  readonly confirmed = output<void>();
  submittedPayload: CompleteProductionPayload | null = null;

  readonly groups: ProductionGroup[] = [];

  get ingredients(): ProductionIngredient[] {
    return this.groups.flatMap((group) => group.ingredients);
  }

  expirationDate = '';
  errorMessage = '';

  ngOnInit(): void {
    const analysis = this.order().analysis;
    if (!analysis) {
      this.errorMessage = 'Não há análise de produção disponível para concluir este pedido.';
      return;
    }

    const available = new Map(analysis.ingredientes.map((item) => [item.id_ingrediente, item]));
    const row = (
      key: string,
      id: number,
      name: string,
      expected: string,
      unit: string | undefined,
    ): ProductionIngredient => {
      const stock = available.get(id);
      const unitLabel = unit ?? stock?.unidade_medida ?? '';
      return {
        key,
        id,
        name,
        lot: `Disponível: ${formatQuantity(stock?.disponivel ?? '0')} ${unitLabel}`.trim(),
        theoreticalQuantity: String(expected),
        theoreticalLabel: formatQuantity(expected),
        quantity: '',
        availableQuantity: stock?.disponivel ?? '0',
        unit: unitLabel,
      };
    };

    // Com a divisão por receita, a confeiteira confere massa, recheio e cobertura
    // separadamente; a API soma as linhas do mesmo ingrediente na baixa.
    if (analysis.receitas?.length) {
      for (const recipe of analysis.receitas) {
        this.groups.push({
          recipeName: recipe.nome,
          ingredients: recipe.ingredientes.map((item) =>
            row(
              `${recipe.id_receita}-${item.id_ingrediente}`,
              item.id_ingrediente,
              item.nome,
              item.necessario,
              item.unidade_medida,
            ),
          ),
        });
      }
      return;
    }

    this.groups.push({
      recipeName: null,
      ingredients: analysis.ingredientes.map((item) =>
        row(
          String(item.id_ingrediente),
          item.id_ingrediente,
          item.nome,
          item.necessario,
          item.unidade_medida,
        ),
      ),
    });
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  close(): void {
    this.closed.emit();
  }

  confirm(): void {
    if (!this.expirationDate || this.ingredients.length === 0) {
      this.errorMessage = 'Informe a validade e os consumos reais antes de concluir a produção.';
      return;
    }

    const consumos: ProductionConsumption[] = [];
    for (const ingredient of this.ingredients) {
      if (!ingredient.quantity.trim()) {
        this.errorMessage = `Informe o consumo real de ${ingredient.name}; use zero se não houve consumo.`;
        return;
      }
      const quantity = Number(ingredient.quantity);
      if (!Number.isFinite(quantity) || quantity < 0) {
        this.errorMessage = `Quantidade inválida para o ingrediente ${ingredient.name}.`;
        return;
      }
      consumos.push({
        ingrediente_id: ingredient.id,
        quantidade: String(quantity),
      });
    }

    this.errorMessage = '';
    this.submittedPayload = {
      data_validade: this.expirationDate,
      consumos,
    };
    this.confirmed.emit();
  }
}
