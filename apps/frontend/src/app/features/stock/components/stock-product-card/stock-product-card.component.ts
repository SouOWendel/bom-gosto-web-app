import { Component, input, output } from '@angular/core';
import {
  LucideCalendar,
  LucideDynamicIcon,
  LucideFileText,
  LucidePencil,
  provideLucideIcons,
} from '@lucide/angular';
import { StockProductCardItem } from './stock-product-card.model';

@Component({
  selector: 'app-stock-product-card',
  standalone: true,
  imports: [LucideDynamicIcon],
  providers: [provideLucideIcons(LucideCalendar, LucideFileText, LucidePencil)],
  templateUrl: './stock-product-card.component.html',
  styleUrls: ['./stock-product-card.component.scss'],
})
export class StockProductCardComponent {
  readonly product = input.required<StockProductCardItem>();

  readonly technicalSheet = output<StockProductCardItem>();
  readonly details = output<StockProductCardItem>();
  readonly pricing = output<StockProductCardItem>();
  readonly edit = output<StockProductCardItem>();
}
