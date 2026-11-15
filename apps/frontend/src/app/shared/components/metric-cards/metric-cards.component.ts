import { Component, input } from '@angular/core';
import {
  LucideDynamicIcon,
  provideLucideIcons,
  LucideBanknote,
  LucideCalendar,
  LucideReceipt,
  LucideTrendingUp,
  LucidePackage,
  LucideCircleAlert,
  LucideShoppingBag,
} from '@lucide/angular';
import { MetricCardItem } from './metric-cards.model';

@Component({
  selector: 'app-metric-cards',
  standalone: true,
  imports: [LucideDynamicIcon],
  providers: [
    provideLucideIcons(
      LucideBanknote,
      LucideCalendar,
      LucideReceipt,
      LucideTrendingUp,
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
