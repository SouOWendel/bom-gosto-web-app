import { Component, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  LucideDynamicIcon,
  provideLucideIcons,
  LucideCalendar,
  LucideSearch,
} from '@lucide/angular';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [CommonModule, LucideDynamicIcon],
  providers: [provideLucideIcons(LucideCalendar, LucideSearch)],
  templateUrl: './topbar.component.html',
  styleUrls: ['./topbar.component.scss'],
})
export class TopbarComponent {
  readonly dataAtual = computed<string>(() => {
    const now = new Date(2026, 8, 15); // 15 de Setembro de 2026 (mês é 0-indexado)
    return now.toLocaleDateString('pt-BR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    });
  });
}
