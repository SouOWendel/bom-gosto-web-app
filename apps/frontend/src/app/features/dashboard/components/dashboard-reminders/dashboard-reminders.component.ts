import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  LucideDynamicIcon,
  provideLucideIcons,
  LucidePlus,
  LucideEdit,
  LucideCheck,
} from '@lucide/angular';

export interface Lembrete {
  id: number;
  titulo: string;
  prioridade: 'Alta' | 'Média' | 'Baixa';
  responsavel: string;
  descricao: string;
  status: 'hoje' | 'em_andamento' | 'pendente';
  statusLabel: string;
}

@Component({
  selector: 'app-dashboard-reminders',
  standalone: true,
  imports: [CommonModule, LucideDynamicIcon],
  providers: [provideLucideIcons(LucidePlus, LucideEdit, LucideCheck)],
  templateUrl: './dashboard-reminders.component.html',
  styleUrls: ['./dashboard-reminders.component.scss'],
})
export class DashboardRemindersComponent {
  readonly lembretes = signal<Lembrete[]>([
    {
      id: 1,
      titulo: 'Comprar farinha de trigo extra',
      prioridade: 'Alta',
      responsavel: 'Chef Rosangela',
      descricao:
        'Confirmar estoque antes do próximo lote de producão. Precisamos de pelo menos 5kg.',
      status: 'hoje',
      statusLabel: 'Hoje',
    },
    {
      id: 2,
      titulo: 'Revisar cronograma de fornos',
      prioridade: 'Média',
      responsavel: 'Equipe de Produção',
      descricao:
        'Verificar disponibilidade dos fornos para os pedidos da semana e ajustar turnos conforme necessário.',
      status: 'em_andamento',
      statusLabel: 'Em andamento',
    },
    {
      id: 3,
      titulo: 'Enviar lembrete de pagamento',
      prioridade: 'Baixa',
      responsavel: 'Financeiro',
      descricao: 'Contatar clientes com pagamentos pendentes para os pedidos da próxima semana.',
      status: 'pendente',
      statusLabel: 'Pendente',
    },
  ]);

  concluirLembrete(id: number): void {
    this.lembretes.update((lista) => lista.filter((l) => l.id !== id));
  }
}
