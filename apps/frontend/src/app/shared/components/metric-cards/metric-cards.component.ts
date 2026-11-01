import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  LucideDynamicIcon,
  provideLucideIcons,
  LucideBanknote,
  LucideCalendar,
  LucideReceipt,
  LucideTrendingUp,
  LucideTrendingDown,
  LucidePackage,
  LucideCircleAlert,
  LucideShoppingBag,
} from '@lucide/angular';
import { MetricCardItem } from './metric-cards.model';

@Component({
  selector: 'app-metric-cards',
  standalone: true,
  imports: [CommonModule, LucideDynamicIcon],
  providers: [
    provideLucideIcons(
      LucideBanknote,
      LucideCalendar,
      LucideReceipt,
      LucideTrendingUp,
      LucideTrendingDown,
      LucidePackage,
      LucideCircleAlert,
      LucideShoppingBag,
    ),
  ],
  templateUrl: './metric-cards.component.html',
  styleUrls: ['./metric-cards.component.scss'],
})
export class MetricCardsComponent {
  readonly items = input<MetricCardItem[]>([]);
}
