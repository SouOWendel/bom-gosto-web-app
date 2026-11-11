import { Component, input, output } from '@angular/core';
import {
  LucideDynamicIcon,
  provideLucideIcons,
  LucideCakeSlice,
  LucideCandy,
  LucideClock,
  LucideGift,
  LucideMapPin,
  LucidePhone,
  LucideFileText,
  LucideCircleCheck,
  LucidePackage,
} from '@lucide/angular';
import { PedidoSimulado } from '../../dashboard.component';
import { ButtonComponent } from '../../../../shared/components/button/button.component';

@Component({
  selector: 'app-dashboard-agenda',
  standalone: true,
  imports: [LucideDynamicIcon, ButtonComponent],
  providers: [
    provideLucideIcons(
      LucideCakeSlice,
      LucideCandy,
      LucideGift,
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

  readonly abas: Array<{ valor: 'todos' | 'bolo' | 'doce' | 'kit'; rotulo: string }> = [
    { valor: 'todos', rotulo: 'Todos' },
    { valor: 'bolo', rotulo: 'Bolos' },
    { valor: 'doce', rotulo: 'Doces' },
    { valor: 'kit', rotulo: 'Kits' },
  ];

  readonly iconeCategoria: Record<string, string> = {
    bolo: 'cake-slice',
    doce: 'candy',
    kit: 'gift',
  };

  // Mesmas cores de status usadas na tela de Pedidos (ver .badge em styles.scss).
  readonly statusBadge: Record<string, string> = {
    confirmado: 'badge--warning',
    em_producao: 'badge--info',
    pronto: 'badge--success',
    entregue: 'badge--neutral',
  };

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
