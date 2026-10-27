import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import {
  LucideDynamicIcon,
  provideLucideIcons,
  LucideTrendingUp,
  LucideReceipt,
  LucideBanknote,
  LucideCakeSlice,
  LucideTriangleAlert,
  LucideCalendar,
  LucideChevronLeft,
  LucideChevronRight,
  LucideClock,
  LucideMapPin,
  LucidePlus,
  LucidePhone,
  LucideFileText,
  LucideCircleCheck,
  LucidePackage,
  LucideShoppingBag,
  LucideSparkles,
} from '@lucide/angular';

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
  categoria: CategoriaPedido;
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
  imports: [CommonModule, RouterLink, LucideDynamicIcon],
  providers: [
    provideLucideIcons(
      LucideTrendingUp,
      LucideReceipt,
      LucideBanknote,
      LucideCakeSlice,
      LucideTriangleAlert,
      LucideCalendar,
      LucideChevronLeft,
      LucideChevronRight,
      LucideClock,
      LucideMapPin,
      LucidePlus,
      LucidePhone,
      LucideFileText,
      LucideCircleCheck,
      LucidePackage,
      LucideShoppingBag,
      LucideSparkles,
    ),
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent {
  // Informações do Cabeçalho
  readonly saudacao = 'Bom dia, Chef Rosangela!';
  readonly statusAtelie = 'Ateliê em Produção';
  readonly dataFormatada = 'Segunda-feira, 15 de Setembro de 2026';
  readonly mesAno = 'Setembro 2026';

  // Dia atualmente selecionado no calendário (YYYY-MM-DD)
  readonly dataSelecionada = signal<string>('2026-09-15');

  // Filtro de categorias da agenda: 'todos' | 'bolo' | 'doce' | 'kit'
  readonly filtroCategoria = signal<string>('todos');

  // Cards de Métricas do Cabeçalho (baseados no protótipo Figura 8)
  readonly cardsResumo: ResumoCard[] = [
    {
      titulo: 'VENDAS DE HOJE',
      valor: 'R$ 840,00',
      subtexto: '+14% em relação à meta do dia',
      tipo: 'vendas',
      icone: 'banknote',
    },
    {
      titulo: 'PEDIDOS AGENDADOS',
      valor: '3 pedidos',
      subtexto: '1 pronto • 1 em finalização • 1 confirmado',
      tipo: 'pedidos',
      icone: 'receipt',
    },
    {
      titulo: 'VALOR MÉDIO POR PEDIDO',
      valor: 'R$ 181,60',
      subtexto: 'Alta complexidade artesanal garantida',
      tipo: 'ticket',
      icone: 'cake-slice',
    },
    {
      titulo: 'ESTOQUE BAIXO',
      valor: 'Leite Condensado Moça',
      subtexto: 'Restam apenas 3 latas no inventário',
      tipo: 'alerta',
      tagAcao: 'Repor Estoque',
      icone: 'triangle-alert',
    },
  ];

  // Base simulada de pedidos (alinhada aos dados do backend/seed e protótipo)
  readonly pedidos = signal<PedidoSimulado[]>([
    {
      id: 1,
      data: '2026-09-15',
      horario: '10:00',
      modalidade: 'RETIRADA',
      titulo: 'Bolo de Chocolate Belga 2kg',
      descricao: 'Massa cacau 100%, recheio trufado e granulado belga callebaut',
      categoria: 'bolo',
      status: 'pronto',
      statusLabel: 'Pronto para Retirada',
      cliente: 'Ana Souza',
      telefone: '(11) 98765-4321',
      pagamentoInfo: 'PIX Confirmado: R$ 120,00',
    },
    {
      id: 2,
      data: '2026-09-15',
      horario: '14:30',
      modalidade: 'RETIRADA',
      titulo: 'Kit Festa Celebração',
      descricao: 'Bolo 2,5kg + 50 Brigadeiros Nobres',
      categoria: 'kit',
      status: 'em_producao',
      statusLabel: 'Em Produção',
      cliente: 'Beatriz Santos',
      telefone: '(11) 97755-4411',
      etapaProducao: 'Cozinhando & Cobertura • 75% Concluído',
      progressoPct: 75,
      pagamentoInfo: 'Sinal 50%: R$ 245,00 (R$ 245 restante)',
      botaoAcao: 'Avançar para Pronto',
    },
    {
      id: 3,
      data: '2026-09-15',
      horario: '18:00',
      modalidade: 'DELIVERY',
      titulo: 'Bolo Red Velvet Especial',
      descricao: 'Decoração floral com frutas vermelhas',
      categoria: 'bolo',
      status: 'confirmado',
      statusLabel: 'Confirmado',
      cliente: 'Beatriz Santos',
      telefone: '(11) 97755-4411',
      endereco: 'Entrega em Domicílio (Zona Sul)',
      pagamentoInfo: 'Sinal 50%: R$ 90,00 (R$ 90 restante)',
      botaoAcao: 'Iniciar Preparo',
    },
    {
      id: 4,
      data: '2026-09-19',
      horario: '16:00',
      modalidade: 'RETIRADA',
      titulo: 'Bolo 1kg massa branca + 50 salgados',
      categoria: 'kit',
      status: 'confirmado',
      statusLabel: 'Confirmado',
      cliente: 'Vivi',
      telefone: '(11) 97456-1003',
      pagamentoInfo: 'Valor Total: R$ 162,63',
      botaoAcao: 'Iniciar Preparo',
    },
    {
      id: 5,
      data: '2026-09-22',
      horario: '14:00',
      modalidade: 'RETIRADA',
      titulo: 'Caseirinho vulcão formigueiro',
      categoria: 'bolo',
      status: 'confirmado',
      statusLabel: 'Confirmado',
      cliente: 'Natália',
      telefone: '(11) 98123-1485',
      pagamentoInfo: 'Valor Total: R$ 40,00',
      botaoAcao: 'Iniciar Preparo',
    },
    {
      id: 6,
      data: '2026-09-26',
      horario: '17:30',
      modalidade: 'RETIRADA',
      titulo: 'Bolo 1kg massa branca delícia de limão',
      categoria: 'bolo',
      status: 'confirmado',
      statusLabel: 'Confirmado',
      cliente: 'Licilene Alves',
      telefone: '(11) 97654-3210',
      pagamentoInfo: 'Sinal 50%: R$ 60,45',
      botaoAcao: 'Iniciar Preparo',
    },
  ]);

  // Dias da semana para cabeçalho do calendário
  readonly diasSemana = ['DOM', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB'];

  // Geração da grade de Setembro de 2026 (1 de set. começou numa terça-feira)
  readonly diasCalendario = computed<DiaCalendario[]>(() => {
    const dias: DiaCalendario[] = [];
    const totalDias = 30;
    const diaSemanaInicio = 2; // Terça-feira (0=Dom, 1=Seg, 2=Ter)

    // Preenchimento de dias vazios antes do dia 1
    for (let i = 0; i < diaSemanaInicio; i++) {
      dias.push({
        numero: null,
        dataStr: '',
        isHoje: false,
        categorias: [],
      });
    }

    const mapaCategorias: Record<number, CategoriaPedido[]> = {
      4: ['doce'],
      5: ['doce'],
      12: ['bolo'],
      15: ['bolo', 'kit'],
      19: ['bolo', 'kit', 'doce'],
      22: ['bolo'],
      26: ['bolo'],
    };

    for (let n = 1; n <= totalDias; n++) {
      const diaFormatado = n < 10 ? `0${n}` : `${n}`;
      const dataStr = `2026-09-${diaFormatado}`;
      dias.push({
        numero: n,
        dataStr,
        isHoje: n === 15,
        categorias: mapaCategorias[n] || [],
      });
    }

    return dias;
  });

  // Pedidos do dia selecionado
  readonly pedidosDoDia = computed(() => {
    const sel = this.dataSelecionada();
    return this.pedidos().filter((p) => p.data === sel);
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

  // Interatividade simulada: transição de status do pedido
  avancarStatus(pedido: PedidoSimulado): void {
    this.pedidos.update((lista) =>
      lista.map((p) => {
        if (p.id !== pedido.id) return p;

        if (p.status === 'confirmado') {
          return {
            ...p,
            status: 'em_producao',
            statusLabel: 'Em Produção',
            etapaProducao: 'Massa & Recheio em preparo',
            progressoPct: 35,
            botaoAcao: 'Avançar para Pronto',
          };
        }

        if (p.status === 'em_producao') {
          return {
            ...p,
            status: 'pronto',
            statusLabel: 'Pronto para Retirada',
            progressoPct: 100,
            botaoAcao: undefined,
          };
        }

        return p;
      }),
    );
  }

  abrirWhatsApp(telefone: string, cliente: string): void {
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

  getIcon(icone: string): string {
    const aliases: Record<string, string> = {
      'alert-triangle': 'triangle-alert',
      'check-circle-2': 'circle-check',
    };
    return aliases[icone] ?? icone;
  }
}
