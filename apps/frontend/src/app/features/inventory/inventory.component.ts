import { Component } from '@angular/core';
import { MetricCardsComponent } from '../../shared/components/metric-cards/metric-cards.component';
import { MetricCardItem } from '../../shared/components/metric-cards/metric-cards.model';
import { PageGreetingComponent } from '../../shared/components/page-greeting/page-greeting.component';
import { PageAction } from '../../shared/components/page-greeting/page-greeting.model';

interface InventoryItem {
  name: string;
  code: string;
  lot: string;
  level: string;
  percentage: number;
  unit: string;
  packaging: string;
  minimum: string;
  status: 'low' | 'normal' | 'critical';
  statusLabel: string;
  expiration: string;
  expirationDetail: string;
  cost: string;
  lastMovement: string;
  author: string;
}

@Component({
  selector: 'app-inventory',
  standalone: true,
  imports: [PageGreetingComponent, MetricCardsComponent],
  templateUrl: './inventory.component.html',
  styleUrls: ['./inventory.component.scss'],
})
export class InventoryComponent {
  readonly greetingActions: PageAction[] = [
    { label: 'Entrada / Saída Rápida', icon: 'filter', variant: 'secondary' },
    { label: 'Novo Insumo', icon: 'plus', variant: 'primary' },
  ];

  readonly summaryCards: MetricCardItem[] = [
    {
      label: 'Total de itens',
      value: '64',
      subtext: 'Ativos catalogados',
      icon: 'package',
      variant: 'destaque',
    },
    {
      label: 'Valor em estoque',
      value: 'R$ 4.820,00',
      subtext: 'Custo médio ponderado',
      icon: 'banknote',
      variant: 'neutro',
    },
    {
      label: 'Estoque baixo',
      value: '4',
      subtext: 'Itens em alerta',
      icon: 'circle-alert',
      variant: 'alerta',
    },
    {
      label: 'Itens esgotados',
      value: '1',
      subtext: 'Item bloqueado',
      icon: 'shopping-bag',
      variant: 'neutro',
    },
  ];

  readonly inventoryItems: InventoryItem[] = [
    {
      name: 'Leite Condensado Moça 395g',
      code: 'INS-0012',
      lot: 'Lote 2025-A',
      level: '8 latas',
      percentage: 53,
      unit: 'Lata 395g',
      packaging: 'Cx. c/ 24',
      minimum: '15 latas',
      status: 'low',
      statusLabel: 'Baixo',
      expiration: 'Sem data',
      expirationDetail: 'Verificar',
      cost: 'R$ 7,90',
      lastMovement: 'Hoje, 09:15',
      author: 'Chef Rosangela',
    },
    {
      name: 'Chocolate Meio Amargo 1kg',
      code: 'INS-0048',
      lot: 'Lote 2025-B',
      level: '12 barras',
      percentage: 80,
      unit: 'Barra 1kg',
      packaging: 'Cx. c/ 6',
      minimum: '9 barras',
      status: 'normal',
      statusLabel: 'Normal',
      expiration: '15/06/2026',
      expirationDetail: 'Preventivo',
      cost: 'R$ 42,90',
      lastMovement: 'Ontem, 16:40',
      author: 'Chef Marcelo',
    },
    {
      name: 'Cacau em Pó 250g',
      code: 'INS-0051',
      lot: 'Lote 2025-C',
      level: '3 pacotes',
      percentage: 20,
      unit: 'Pacote 250g',
      packaging: 'Cx. c/ 12',
      minimum: '6 pacotes',
      status: 'critical',
      statusLabel: 'Crítico',
      expiration: 'Há 6 dias',
      expirationDetail: 'Crítico',
      cost: 'R$ 18,50',
      lastMovement: 'Hoje, 08:10',
      author: 'Chef Rosangela',
    },
    {
      name: 'Nozes Picadas 200g',
      code: 'INS-0067',
      lot: 'Lote 2025-D',
      level: '18 sacos',
      percentage: 90,
      unit: 'Saco 200g',
      packaging: 'Cx. c/ 20',
      minimum: '12 sacos',
      status: 'normal',
      statusLabel: 'Normal',
      expiration: '22/06/2026',
      expirationDetail: 'Preventivo',
      cost: 'R$ 24,80',
      lastMovement: 'Ontem, 17:20',
      author: 'Chef Marcelo',
    },
    {
      name: 'Amêndoas Fatiadas 250g',
      code: 'INS-0073',
      lot: 'Lote 2025-E',
      level: '5 pacotes',
      percentage: 33,
      unit: 'Pacote 250g',
      packaging: 'Cx. c/ 15',
      minimum: '10 pacotes',
      status: 'low',
      statusLabel: 'Baixo',
      expiration: '03/07/2026',
      expirationDetail: 'Atenção',
      cost: 'R$ 31,20',
      lastMovement: 'Hoje, 07:55',
      author: 'Chef Rosangela',
    },
  ];
}
