import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { DashboardComponent } from './dashboard.component';
import { Order } from '../../core/models/api.model';
import { DomainApiService } from '../../core/services/domain-api.service';
import { of } from 'rxjs';

const today = (() => {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(
    date.getDate(),
  ).padStart(2, '0')}`;
})();

function createOrder(id: number, status: Order['status']): Order {
  return {
    id_pedido: id,
    cliente: id,
    tipo: 'externo',
    subtipo: 'vitrine',
    status,
    data_entrega: today,
    horario_entrega: '12:00',
    valor_total: '100.00',
    valor_sinal: '50.00',
    endereco_entrega: null,
    forma_pagamento: 'pix',
    itens: [{ produto: id, receita: null, quantidade: 1, preco_unitario: '100.00' }],
  };
}

const apiOrders: Order[] = [
  createOrder(1, 'pedido_feito'),
  createOrder(2, 'em_producao'),
  createOrder(3, 'producao_concluida'),
];

describe('DashboardComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        provideRouter([]),
        {
          provide: DomainApiService,
          useValue: { getOrders: () => of(apiOrders) },
        },
      ],
    }).compileComponents();
  });

  it('deve instanciar o componente do dashboard', () => {
    const fixture = TestBed.createComponent(DashboardComponent);
    const component = fixture.componentInstance;
    expect(component).toBeTruthy();
  });

  it('deve carregar os pedidos da API para o dia atual', () => {
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();
    const component = fixture.componentInstance;
    expect(component.dataSelecionada()).toBe(today);
    expect(component.pedidosDoDia().length).toBe(3);
  });

  it('não deve inventar categorias ausentes na resposta da API', () => {
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();
    const component = fixture.componentInstance;
    component.setFiltro('bolo');
    expect(component.pedidosFiltrados().length).toBe(0);
    expect(component.pedidos().every((order) => order.categoria === null)).toBe(true);
  });

  it('deve indicar quando a API não fornece a data para calcular vendas de hoje', () => {
    const component = TestBed.createComponent(DashboardComponent).componentInstance;
    expect(component.metricas[0].value).toBe('—');
  });
});
