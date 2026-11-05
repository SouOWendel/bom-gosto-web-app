import { Component, HostListener, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LucideCheck, LucideDynamicIcon, provideLucideIcons } from '@lucide/angular';
import { InputTextComponent } from '../input-text/input-text.component';

interface ProductionIngredient {
  name: string;
  lot: string;
  theoreticalQuantity: string;
  quantity: string;
  unit: string;
}

interface ProductionOrder {
  id: string;
  item: string;
}

@Component({
  selector: 'app-complete-production-modal',
  standalone: true,
  imports: [FormsModule, InputTextComponent, LucideDynamicIcon],
  providers: [provideLucideIcons(LucideCheck)],
  templateUrl: './complete-production-modal.component.html',
  styleUrls: ['./complete-production-modal.component.scss'],
})
export class CompleteProductionModalComponent {
  readonly order = input.required<ProductionOrder>();
  readonly closed = output<void>();
  readonly confirmed = output<void>();

  readonly ingredients: ProductionIngredient[] = [
    {
      name: 'Farinha de trigo',
      lot: 'Lote MP-1842',
      theoreticalQuantity: '12,5 kg',
      quantity: '12.5',
      unit: 'kg',
    },
    {
      name: 'Açúcar refinado',
      lot: 'Lote MP-2019',
      theoreticalQuantity: '4,2 kg',
      quantity: '4.2',
      unit: 'kg',
    },
    {
      name: 'Manteiga sem sal',
      lot: 'Lote MP-2271',
      theoreticalQuantity: '2,8 kg',
      quantity: '2.8',
      unit: 'kg',
    },
    {
      name: 'Ovos pasteurizados',
      lot: 'Lote MP-2310',
      theoreticalQuantity: '3,5 L',
      quantity: '3.5',
      unit: 'L',
    },
    {
      name: 'Fermento químico',
      lot: 'Lote MP-1760',
      theoreticalQuantity: '0,18 kg',
      quantity: '0.18',
      unit: 'kg',
    },
  ];

  expirationDate = '';

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  close(): void {
    this.closed.emit();
  }

  confirm(): void {
    if (!this.expirationDate) {
      return;
    }

    this.confirmed.emit();
  }
}
