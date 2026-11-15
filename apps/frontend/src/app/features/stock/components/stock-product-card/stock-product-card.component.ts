import { Component, input, output } from '@angular/core';
import {
  LucideCalendar,
  LucideDynamicIcon,
  LucidePackage,
  LucidePencil,
  provideLucideIcons,
} from '@lucide/angular';
import { ButtonComponent } from '../../../../shared/components/button/button.component';
import { StockProductCardItem } from './stock-product-card.model';

@Component({
  selector: 'app-stock-product-card',
  standalone: true,
  imports: [LucideDynamicIcon, ButtonComponent],
  providers: [provideLucideIcons(LucideCalendar, LucidePackage, LucidePencil)],
  templateUrl: './stock-product-card.component.html',
  styleUrls: ['./stock-product-card.component.scss'],
})
export class StockProductCardComponent {
  readonly product = input.required<StockProductCardItem>();
  readonly edit = output<void>();

  // Mesma cor do semáforo de validade usada no inventário (ver .badge em styles.scss).
  readonly statusBadge: Record<StockProductCardItem['status'], string> = {
    critico: 'badge--danger',
    atencao: 'badge--warning',
    preventivo: 'badge--info',
    normal: 'badge--success',
  };
}
