import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { DashboardComponent } from './dashboard.component';

describe('DashboardComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('deve instanciar o componente do dashboard', () => {
    const fixture = TestBed.createComponent(DashboardComponent);
    const component = fixture.componentInstance;
    expect(component).toBeTruthy();
  });

  it('deve inicializar com o dia 15 de setembro selecionado e 3 pedidos simulados', () => {
    const fixture = TestBed.createComponent(DashboardComponent);
    const component = fixture.componentInstance;
    expect(component.dataSelecionada()).toBe('2026-09-15');
    expect(component.pedidosDoDia().length).toBe(3);
  });

  it('deve permitir filtrar os pedidos por categoria', () => {
    const fixture = TestBed.createComponent(DashboardComponent);
    const component = fixture.componentInstance;
    component.setFiltro('bolo');
    expect(component.pedidosFiltrados().length).toBe(2);
  });
});
