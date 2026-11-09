import { Component, computed, input, output } from '@angular/core';
import {
  LucideCalendar,
  LucideDynamicIcon,
  LucideMenu,
  LucideX,
  provideLucideIcons,
} from '@lucide/angular';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [LucideDynamicIcon],
  providers: [provideLucideIcons(LucideCalendar, LucideMenu, LucideX)],
  templateUrl: './topbar.component.html',
  styleUrls: ['./topbar.component.scss'],
})
export class TopbarComponent {
  // O botão de menu só aparece até 1024px, quando a sidebar fica recolhida.
  readonly menuOpen = input(false);
  readonly menuToggle = output<void>();

  // Ex.: "Segunda-feira, 9 de novembro" (só a primeira letra em maiúscula, como no português).
  readonly dataAtual = computed<string>(() => {
    const texto = new Date().toLocaleDateString('pt-BR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    });
    return texto.charAt(0).toUpperCase() + texto.slice(1);
  });
}
