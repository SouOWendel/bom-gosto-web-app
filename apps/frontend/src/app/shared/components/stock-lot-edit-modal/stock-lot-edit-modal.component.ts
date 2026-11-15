import { Component, HostListener, OnInit, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LucideDynamicIcon, LucideX, provideLucideIcons } from '@lucide/angular';
import { ButtonComponent } from '../button/button.component';
import { InputTextComponent } from '../input-text/input-text.component';
import { StockLot } from '../../../core/models/api.model';
import { parseDecimal, toDisplayDecimal } from '../../../core/utils/format';

// Edita quantidade, validade e custo de um lote de produto pronto (RF11), sem exclusão.
@Component({
  selector: 'app-stock-lot-edit-modal',
  standalone: true,
  imports: [FormsModule, ButtonComponent, InputTextComponent, LucideDynamicIcon],
  providers: [provideLucideIcons(LucideX)],
  templateUrl: './stock-lot-edit-modal.component.html',
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
    this.quantity = toDisplayDecimal(lot.quantidade_disponivel);
    this.expiration = lot.data_validade ?? '';
    this.cost = lot.custo ?? '';
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  close(): void {
    this.closed.emit();
  }

  submit(): void {
    const quantity = parseDecimal(this.quantity);
    if (!/^\d+(\.\d{1,2})?$/.test(quantity)) {
      this.errorMessage = 'Informe a quantidade com até duas casas decimais (zero ou mais).';
      return;
    }
    const cost = parseDecimal(this.cost);
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
}
