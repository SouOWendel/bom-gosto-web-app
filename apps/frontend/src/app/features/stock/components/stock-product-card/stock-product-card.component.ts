import { Component, input } from '@angular/core';
import {
  LucideCalendar,
  LucideDynamicIcon,
  LucidePackage,
  provideLucideIcons,
} from '@lucide/angular';
import { StockProductCardItem } from './stock-product-card.model';

@Component({
  selector: 'app-stock-product-card',
  standalone: true,
  imports: [LucideDynamicIcon],
  providers: [provideLucideIcons(LucideCalendar, LucidePackage)],
  templateUrl: './stock-product-card.component.html',
  styleUrls: ['./stock-product-card.component.scss'],
})
export class StockProductCardComponent {
  readonly product = input.required<StockProductCardItem>();

  // Mesma cor do semáforo de validade usada no inventário (ver .badge em styles.scss).
  readonly statusBadge: Record<StockProductCardItem['status'], string> = {
    critico: 'badge--danger',
    atencao: 'badge--warning',
    preventivo: 'badge--info',
    normal: 'badge--success',
  };
}
