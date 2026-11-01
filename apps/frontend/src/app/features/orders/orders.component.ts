import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  LucideDynamicIcon,
  LucideCalendar,
  LucideChevronDown,
  LucideMessageSquare,
  LucidePencil,
  LucidePrinter,
  LucideSearch,
  LucideTrash2,
  provideLucideIcons,
} from '@lucide/angular';
import { MetricCardsComponent } from '../../shared/components/metric-cards/metric-cards.component';
import { MetricCardItem } from '../../shared/components/metric-cards/metric-cards.model';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';

type OrderStatus = 'retirada' | 'producao' | 'confirmado' | 'pendente';
type OrderCategory = 'bolos' | 'doces' | 'kits';

interface Order {
  id: string;
  customer: string;
  phone: string;
  address: string;
  item: string;
  category: OrderCategory;
  total: string;
  payment: string;
  status: OrderStatus;
  statusLabel: string;
  schedule: string;
  detail: string;
  action: string;
  image: string;
}

@Component({
  selector: 'app-orders',
  standalone: true,
  imports: [CommonModule, LucideDynamicIcon, PageGreetingComponent, MetricCardsComponent],
  providers: [provideLucideIcons(LucideCalendar, LucideChevronDown, LucideMessageSquare, LucidePencil, LucidePrinter, LucideSearch, LucideTrash2)],
  templateUrl: './orders.component.html',
  styleUrls: ['./orders.component.scss'],
})
export class OrdersComponent {
  readonly greetingActions: PageAction[] = [
    { label: 'Filtro Avançado', icon: 'filter', variant: 'secondary' },
    { label: '+ Novo Pedido', icon: 'plus', variant: 'primary' },
    { label: 'Cancelar em produção', variant: 'secondary' },
  ];

  readonly summaryCards: MetricCardItem[] = [
    { label: 'Hoje em produção', value: 'R$ 640,00', subtext: '4 entregas programadas', icon: 'calendar', variant: 'destaque' },
    { label: 'Prontos p/ retirada', value: '5 encomendas', subtext: 'Aguardando clientes', icon: 'package', variant: 'alerta' },
    { label: 'Pagamentos pendentes', value: 'R$ 340,00', subtext: '2 pedidos com saldo', icon: 'banknote', variant: 'pedidos' },
    { label: 'Meta mensal concluída', value: '78% atingido', subtext: 'Meta em andamento', icon: 'trending-up', variant: 'neutro' },
  ];

  readonly searchTerm = signal('');
  readonly selectedCategory = signal<'todos' | OrderCategory>('todos');
  readonly selectedStatus = signal<'todos' | OrderStatus>('todos');

  readonly orders = signal<Order[]>([
    {
      id: '#1084',
      customer: 'Ana Souza',
      phone: '(11) 98765-4321',
      address: 'São Paulo - SP',
      item: 'Bolo Trufado Belga 1,5kg',
      category: 'bolos',
      total: 'R$ 120,00',
      payment: 'pago',
      status: 'retirada',
      statusLabel: 'Retirada',
      schedule: 'Hoje • 10:00',
      detail: 'Finalizado às 09:15',
      action: 'Ver Detalhes',
      image: '/images/auth-cake.jpg',
    },
    {
      id: '#1085',
      customer: 'João Pedro',
      phone: '(11) 97123-8899',
      address: 'Moema, SP',
      item: 'Kit Festa Aniversário',
      category: 'kits',
      total: 'R$ 245,00',
      payment: '50% sinal pago',
      status: 'producao',
      statusLabel: 'Em produção',
      schedule: 'Hoje • 14:30',
      detail: '75% concluído',
      action: 'Concluir Produção',
      image: '/images/auth-cake.jpg',
    },
    {
      id: '#1086',
      customer: 'Beatriz Santos',
      phone: '(11) 99442-1100',
      address: 'Jardins, SP',
      item: 'Bolo Red Velvet Frutas Vermelhas',
      category: 'bolos',
      total: 'R$ 180,00',
      payment: 'Na entrega',
      status: 'confirmado',
      statusLabel: 'Confirmado',
      schedule: 'Hoje • 18:00',
      detail: 'Aguardando início',
      action: 'Iniciar Massa e Recheio',
      image: '/images/auth-cake.jpg',
    },
    {
      id: '#1087',
      customer: 'Lucas Almeida',
      phone: '(11) 98777-3322',
      address: 'Pinheiros, SP',
      item: 'Caixa Degustação 25 Brigadeiros',
      category: 'doces',
      total: 'R$ 95,00',
      payment: 'Dinheiro',
      status: 'pendente',
      statusLabel: 'Pendente',
      schedule: 'Amanhã • 11:00',
      detail: 'Pedido via Cardápio Web',
      action: 'Confirmar',
      image: '/images/auth-cake.jpg',
    },
  ]);

  readonly filteredOrders = computed(() => {
    const term = this.searchTerm().trim().toLowerCase();
    const category = this.selectedCategory();
    const status = this.selectedStatus();

    return this.orders().filter((order) => {
      const matchesTerm =
        !term ||
        order.id.toLowerCase().includes(term) ||
        order.customer.toLowerCase().includes(term) ||
        order.item.toLowerCase().includes(term);
      const matchesCategory = category === 'todos' || order.category === category;
      const matchesStatus = status === 'todos' || order.status === status;
      return matchesTerm && matchesCategory && matchesStatus;
    });
  });

  setCategory(category: 'todos' | OrderCategory): void {
    this.selectedCategory.set(category);
  }

  setStatus(status: 'todos' | OrderStatus): void {
    this.selectedStatus.set(status);
  }

  completeOrder(order: Order): void {
    this.orders.update((orders) =>
      orders.map((current) =>
        current.id === order.id
          ? {
              ...current,
              status: 'retirada',
              statusLabel: 'Retirada',
              detail: 'Finalizado agora',
              action: 'Ver Detalhes',
            }
          : current,
      ),
    );
  }
}
