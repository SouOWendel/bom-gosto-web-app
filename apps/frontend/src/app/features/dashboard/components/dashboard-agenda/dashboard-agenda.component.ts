import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import {
  LucideDynamicIcon,
  provideLucideIcons,
  LucideClock,
  LucideMapPin,
  LucidePhone,
  LucideFileText,
  LucideCircleCheck,
  LucidePackage,
} from '@lucide/angular';
import { PedidoSimulado } from '../../dashboard.component';

@Component({
  selector: 'app-dashboard-agenda',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideDynamicIcon],
  providers: [
    provideLucideIcons(
      LucideClock,
      LucideMapPin,
      LucidePhone,
      LucideFileText,
      LucideCircleCheck,
      LucidePackage,
    ),
  ],
  templateUrl: './dashboard-agenda.component.html',
  styleUrls: ['./dashboard-agenda.component.scss'],
})
export class DashboardAgendaComponent {
  readonly pedidosFiltrados = input<PedidoSimulado[]>([]);
  readonly contadoresCategoria = input<{ todos: number; bolo: number; doce: number; kit: number }>({
    todos: 0,
    bolo: 0,
    doce: 0,
    kit: 0,
  });
  readonly filtroCategoria = input<string>('todos');
  readonly dataSelecionada = input<string>('');

  readonly filtroChanged = output<string>();
  readonly avancarStatusEvent = output<PedidoSimulado>();
  readonly abrirWhatsAppEvent = output<{ telefone: string; cliente: string }>();

  getDiaDoMes(dataStr: string): string {
    if (!dataStr) return '';
    return dataStr.split('-')[2] ?? '';
  }

  setFiltro(cat: string): void {
    this.filtroChanged.emit(cat);
  }

  avancarStatus(pedido: PedidoSimulado): void {
    this.avancarStatusEvent.emit(pedido);
  }

  abrirWhatsApp(telefone: string, cliente: string): void {
    this.abrirWhatsAppEvent.emit({ telefone, cliente });
  }
}
