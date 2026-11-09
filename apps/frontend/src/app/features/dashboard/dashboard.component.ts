import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import {
  LucideDynamicIcon,
  provideLucideIcons,
  LucideChevronLeft,
  LucideChevronRight,
  LucidePlus,
} from '@lucide/angular';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';
import { MetricCardItem } from '../../shared/components/metric-cards/metric-cards.model';
import { DashboardAgendaComponent } from './components/dashboard-agenda/dashboard-agenda.component';
import { ButtonComponent } from '../../shared/components/button/button.component';
import { Order } from '../../core/models/api.model';
import { DomainApiService } from '../../core/services/domain-api.service';

export interface ResumoCard {
  titulo: string;
  valor: string;
  subtexto: string;
  tipo: 'vendas' | 'pedidos' | 'ticket' | 'alerta';
  tagAcao?: string;
  icone: string;
}

export type CategoriaPedido = 'bolo' | 'doce' | 'kit';
export type StatusPedido = 'confirmado' | 'em_producao' | 'pronto' | 'entregue';

export interface PedidoSimulado {
  id: number;
  data: string; // YYYY-MM-DD
  horario: string;
  modalidade: 'RETIRADA' | 'DELIVERY';
  titulo: string;
  descricao?: string;
  categoria: CategoriaPedido | null;
  status: StatusPedido;
  statusLabel: string;
  cliente: string;
  telefone: string;
  endereco?: string;
  pagamentoInfo: string;
  etapaProducao?: string;
  progressoPct?: number;
  botaoAcao?: string;
}

export interface DiaCalendario {
  numero: number | null;
  dataStr: string;
  isHoje: boolean;
  categorias: CategoriaPedido[];
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    LucideDynamicIcon,
    PageGreetingComponent,
    DashboardAgendaComponent,
    ButtonComponent,
  ],
  providers: [provideLucideIcons(LucideChevronLeft, LucideChevronRight, LucidePlus)],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit {
  private readonly api = inject(DomainApiService);
  private readonly router = inject(Router);
  private readonly orderData = signal<Order[]>([]);

  // Informações do Cabeçalho
  readonly nomeChef = 'Rosangela';

  // Saudação conforme o horário: "Bom dia", "Boa tarde" ou "Boa noite".
  get saudacao(): string {
    const hora = new Date().getHours();
    return hora < 12 ? 'Bom dia' : hora < 18 ? 'Boa tarde' : 'Boa noite';
  }
  get mesAno(): string {
    return this.monthLabel(this.dataSelecionada());
  }

  readonly greetingActions: PageAction[] = [];

  get metricas(): MetricCardItem[] {
    const orders = this.orderData();
    const scheduled = orders.filter((order) =>
      ['pedido_feito', 'em_producao', 'producao_concluida'].includes(order.status),
    );

    return [
      {
        label: 'VENDAS DE HOJE',
        value: '—',
        icon: 'banknote',
        variant: 'vendas',
        trend: {
          value: 'Data de conclusão não disponível na API',
          direction: 'up',
        },
      },
      {
        label: 'PEDIDOS AGENDADOS',
        value: `${scheduled.length} pedidos`,
        icon: 'receipt',
        variant: 'pedidos',
        subtext: `${orders.filter((order) => order.status === 'producao_concluida').length} prontos • ${orders.filter((order) => order.status === 'em_producao').length} em produção • ${orders.filter((order) => order.status === 'pedido_feito').length} confirmados`,
      },
    ];
  }

  // Dia atualmente selecionado no calendário (YYYY-MM-DD)
  readonly dataSelecionada = signal<string>(this.toDateKey(new Date()));

  // Filtro de categorias da agenda: 'todos' | 'bolo' | 'doce' | 'kit'
  readonly filtroCategoria = signal<string>('todos');

  // Base simulada de pedidos
  readonly pedidos = signal<PedidoSimulado[]>([]);

  ngOnInit(): void {
    this.api.getOrders().subscribe({
      next: (orders) => this.setOrders(orders),
      error: (error) => console.error('Falha ao carregar os pedidos do dashboard.', error),
    });
  }

  // Dias da semana para cabeçalho do calendário
  readonly diasSemana = ['DOM', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB'];

  readonly diasCalendario = computed<DiaCalendario[]>(() => {
    const dias: DiaCalendario[] = [];
    const selecionada = new Date(`${this.dataSelecionada()}T00:00:00`);
    const ano = selecionada.getFullYear();
    const mes = selecionada.getMonth();
    const totalDias = new Date(ano, mes + 1, 0).getDate();
    const diaSemanaInicio = new Date(ano, mes, 1).getDay();

    // Preenchimento de dias vazios antes do dia 1
    for (let i = 0; i < diaSemanaInicio; i++) {
      dias.push({
        numero: null,
        dataStr: '',
        isHoje: false,
        categorias: [],
      });
    }

    const mapaCategorias = new Map<string, Set<CategoriaPedido>>();
    for (const pedido of this.pedidos()) {
      if (
        !pedido.categoria ||
        !pedido.data.startsWith(`${ano}-${String(mes + 1).padStart(2, '0')}`)
      ) {
        continue;
      }
      const categorias = mapaCategorias.get(pedido.data) ?? new Set<CategoriaPedido>();
      categorias.add(pedido.categoria);
      mapaCategorias.set(pedido.data, categorias);
    }

    for (let n = 1; n <= totalDias; n++) {
      const dataStr = this.toDateKey(new Date(ano, mes, n));
      dias.push({
        numero: n,
        dataStr,
        isHoje: dataStr === this.toDateKey(new Date()),
        categorias: [...(mapaCategorias.get(dataStr) ?? [])],
      });
    }

    return dias;
  });

  // Pedidos do dia selecionado, em ordem de horário; sem horário vão para o fim
  readonly pedidosDoDia = computed(() => {
    const sel = this.dataSelecionada();
    const chave = (horario: string) => (/^\d{2}:\d{2}$/.test(horario) ? horario : '99:99');
    return this.pedidos()
      .filter((p) => p.data === sel)
      .sort((a, b) => chave(a.horario).localeCompare(chave(b.horario)) || a.id - b.id);
  });

  // Pedidos filtrados pela aba de categoria
  readonly pedidosFiltrados = computed(() => {
    const filtro = this.filtroCategoria();
    const diaPedidos = this.pedidosDoDia();

    if (filtro === 'todos') {
      return diaPedidos;
    }
    return diaPedidos.filter((p) => p.categoria === filtro);
  });

  // Contadores para as abas
  readonly contadoresCategoria = computed(() => {
    const lista = this.pedidosDoDia();
    return {
      todos: lista.length,
      bolo: lista.filter((p) => p.categoria === 'bolo').length,
      doce: lista.filter((p) => p.categoria === 'doce').length,
      kit: lista.filter((p) => p.categoria === 'kit').length,
    };
  });

  selecionarDia(dia: DiaCalendario): void {
    if (dia.dataStr) {
      this.dataSelecionada.set(dia.dataStr);
    }
  }

  setFiltro(cat: string): void {
    this.filtroCategoria.set(cat);
  }

  navegarMes(delta: number): void {
    const selecionada = new Date(`${this.dataSelecionada()}T00:00:00`);
    const dia = Math.min(
      selecionada.getDate(),
      new Date(selecionada.getFullYear(), selecionada.getMonth() + delta + 1, 0).getDate(),
    );
    this.dataSelecionada.set(
      this.toDateKey(new Date(selecionada.getFullYear(), selecionada.getMonth() + delta, dia)),
    );
  }

  // Interatividade simulada: transição de status do pedido
  avancarStatus(pedido: PedidoSimulado): void {
    if (pedido.status === 'confirmado') {
      this.api.startProduction(pedido.id).subscribe({
        next: () => this.reloadOrders(),
        error: (error) => console.error('Falha ao iniciar a producao do pedido.', error),
      });
      return;
    }
    if (pedido.status === 'em_producao') {
      void this.router.navigate(['/pedidos']);
    }
  }

  abrirWhatsApp(telefone: string, cliente: string): void {
    if (!telefone.trim()) {
      console.error('O pedido nao possui telefone de contato para abrir o WhatsApp.');
      return;
    }
    const numLimpo = telefone.replace(/\D/g, '');
    const msg = encodeURIComponent(
      `Olá ${cliente}! Aqui é da Confeitaria Bom Gosto referente à sua encomenda.`,
    );
    window.open(`https://wa.me/55${numLimpo}?text=${msg}`, '_blank');
  }

  getDiaDoMes(dataStr: string): string {
    if (!dataStr) return '';
    const partes = dataStr.split('-');
    return partes[2] ?? '';
  }

  private reloadOrders(): void {
    this.api.getOrders().subscribe({
      next: (orders) => this.setOrders(orders),
      error: (error) => console.error('Falha ao atualizar os pedidos do dashboard.', error),
    });
  }

  private setOrders(orders: Order[]): void {
    const activeOrders = orders.filter((order) => order.status !== 'cancelado');
    this.orderData.set(orders);
    this.pedidos.set(activeOrders.map((order) => this.toDashboardOrder(order)));
  }

  private toDashboardOrder(order: Order): PedidoSimulado {
    const statusMap: Record<Order['status'], { status: StatusPedido; label: string }> = {
      pedido_feito: { status: 'confirmado', label: 'Confirmado' },
      em_producao: { status: 'em_producao', label: 'Em Produção' },
      producao_concluida: { status: 'pronto', label: 'Produção Concluída' },
      concluido: { status: 'entregue', label: 'Concluído' },
      cancelado: { status: 'entregue', label: 'Cancelado' },
    };
    const status = statusMap[order.status];
    const subtotal = Number(order.valor_total);

    return {
      id: order.id_pedido,
      data: order.data_entrega ?? '',
      horario: order.horario_entrega?.slice(0, 5) ?? '—',
      modalidade: order.endereco_entrega ? 'DELIVERY' : 'RETIRADA',
      titulo: `Pedido #${order.id_pedido}`,
      descricao: `${order.itens.length} item(ns)`,
      categoria: null,
      status: status.status,
      statusLabel: status.label,
      cliente: order.cliente ? `Cliente #${order.cliente}` : 'Cliente não informado',
      telefone: '',
      endereco: order.endereco_entrega ?? undefined,
      pagamentoInfo: `Total: ${this.formatCurrency(subtotal)} • Sinal: ${this.formatCurrency(Number(order.valor_sinal))}`,
      botaoAcao: order.status === 'pedido_feito' ? 'Iniciar Preparo' : undefined,
    };
  }

  private monthLabel(dateKey: string): string {
    if (!dateKey) {
      return '';
    }
    // Ex.: "Novembro de 2026".
    const label = new Date(`${dateKey}T00:00:00`).toLocaleDateString('pt-BR', {
      month: 'long',
      year: 'numeric',
    });
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  private toDateKey(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private formatCurrency(value: number): string {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }
}
