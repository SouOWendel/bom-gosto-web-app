import { Component, OnInit, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LucideDynamicIcon, LucideX, provideLucideIcons } from '@lucide/angular';
import { ButtonComponent } from '../button/button.component';
import { InputTextComponent } from '../input-text/input-text.component';
import { StockLot } from '../../../core/models/api.model';

// Edita quantidade, validade e custo de um lote de produto pronto (RF11), sem exclusão.
@Component({
  selector: 'app-stock-lot-edit-modal',
  standalone: true,
  imports: [FormsModule, ButtonComponent, InputTextComponent, LucideDynamicIcon],
  providers: [provideLucideIcons(LucideX)],
  templateUrl: './stock-lot-edit-modal.component.html',
  styleUrls: ['./stock-lot-edit-modal.component.scss'],
})
export class StockLotEditModalComponent implements OnInit {
  readonly lot = input.required<StockLot>();
  readonly apiError = input<string | null>(null);
  readonly busy = input(false);
  readonly closed = output<void>();
  readonly submitted = output<Partial<StockLot>>();

  quantity = '';
  expiration = '';
  cost = '';
  errorMessage = '';

  ngOnInit(): void {
    const lot = this.lot();
    this.quantity = this.toDisplay(lot.quantidade_disponivel);
    this.expiration = lot.data_validade ?? '';
    this.cost = lot.custo ?? '';
  }

  close(): void {
    this.closed.emit();
  }

  submit(): void {
    const quantity = this.toDecimal(this.quantity);
    if (!/^\d+(\.\d{1,2})?$/.test(quantity)) {
      this.errorMessage = 'Informe a quantidade com até duas casas decimais (zero ou mais).';
      return;
    }
    const cost = this.toDecimal(this.cost);
    if (cost && !/^\d+(\.\d{1,2})?$/.test(cost)) {
      this.errorMessage = 'Informe um custo válido, maior ou igual a zero.';
      return;
    }
    this.errorMessage = '';
    this.submitted.emit({
      quantidade_disponivel: quantity,
      data_validade: this.expiration || null,
      custo: cost || null,
    });
  }

  private toDisplay(value: string): string {
    const number = Number(value);
    return Number.isFinite(number) ? String(number).replace('.', ',') : value;
  }

  // Aceita "1.234,50", "1234,5" ou "1234.5".
  private toDecimal(value: string): string {
    const normalized = value.trim().replace(/[R$\s]/g, '');
    return normalized.includes(',') ? normalized.replace(/\./g, '').replace(',', '.') : normalized;
  }
}
