import { Component, input, output } from '@angular/core';
import {
  LucideArrowLeft,
  LucideDynamicIcon,
  LucidePlus,
  provideLucideIcons,
} from '@lucide/angular';
import { PageAction } from './page-greeting.model';
import { ButtonComponent } from '../button/button.component';

@Component({
  selector: 'app-page-greeting',
  standalone: true,
  imports: [LucideDynamicIcon, ButtonComponent],
  providers: [provideLucideIcons(LucideArrowLeft, LucidePlus)],
  templateUrl: './page-greeting.component.html',
  styleUrls: ['./page-greeting.component.scss'],
})
export class PageGreetingComponent {
  readonly title = input.required<string>();
  readonly subtitle = input<string>('');
  readonly actions = input<PageAction[]>([]);

  readonly actionClick = output<PageAction>();

  onActionClick(action: PageAction): void {
    this.actionClick.emit(action);
  }
}
