import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import {
  LucideDynamicIcon,
  provideLucideIcons,
  LucideCalendar,
  LucidePlus,
  LucideBell,
  LucideClock,
  LucideFilter,
  LucideDownload,
  LucideRefreshCw,
} from '@lucide/angular';
import { PageAction } from './page-greeting.model';

@Component({
  selector: 'app-page-greeting',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideDynamicIcon],
  providers: [
    provideLucideIcons(
      LucideCalendar,
      LucidePlus,
      LucideBell,
      LucideClock,
      LucideFilter,
      LucideDownload,
      LucideRefreshCw,
    ),
  ],
  templateUrl: './page-greeting.component.html',
  styleUrls: ['./page-greeting.component.scss'],
})
export class PageGreetingComponent {
  readonly title = input<string>('Bom dia, Chef Rosangela! 👩‍🍳🔍');
  readonly subtitle = input<string>('🔔 Acesse os atalhos a seguir.');
  readonly actions = input<PageAction[]>([]);

  readonly actionClick = output<PageAction>();

  onActionClick(action: PageAction): void {
    this.actionClick.emit(action);
  }
}
