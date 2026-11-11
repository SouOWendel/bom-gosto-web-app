import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import {
  ApiCollection,
  CancelOrderPayload,
  CompleteProductionPayload,
  Ingredient,
  Order,
  OrderCreationPayload,
  Product,
  ProductionAnalysis,
  Recipe,
  StockLot,
} from '../models/api.model';

@Injectable({ providedIn: 'root' })
export class DomainApiService {
  private readonly http = inject(HttpClient);

  // centraliza as chamadas dos modulos do backend Django
  getIngredients(): Observable<Ingredient[]> {
    return this.list<Ingredient>('/api/inventario/ingrediente/');
  }

  createIngredient(payload: Partial<Ingredient>): Observable<Ingredient> {
    return this.http.post<Ingredient>('/api/inventario/ingrediente/', payload);
  }

  updateIngredient(id: number, payload: Partial<Ingredient>): Observable<Ingredient> {
    return this.http.patch<Ingredient>(`/api/inventario/ingrediente/${id}/`, payload);
  }

  getProducts(): Observable<Product[]> {
    return this.list<Product>('/api/produtos/');
  }

  createProduct(payload: Partial<Product>): Observable<Product> {
    return this.http.post<Product>('/api/produtos/', payload);
  }

  updateProduct(id: number, payload: Partial<Product>): Observable<Product> {
    return this.http.patch<Product>(`/api/produtos/${id}/`, payload);
  }

  getStock(): Observable<StockLot[]> {
    return this.list<StockLot>('/api/estoque/');
  }

  updateStockLot(id: number, payload: Partial<StockLot>): Observable<StockLot> {
    return this.http.patch<StockLot>(`/api/estoque/${id}/`, payload);
  }

  checkAvailability(productId: number, quantity: string): Observable<unknown> {
    const params = new HttpParams().set('id_produto', productId).set('quantidade', quantity);
    return this.http.get('/api/estoque/disponibilidade/', { params });
  }

  getRecipes(): Observable<Recipe[]> {
    return this.list<Recipe>('/api/producao/receitas/');
  }

  createRecipe(payload: Partial<Recipe>): Observable<Recipe> {
    return this.http.post<Recipe>('/api/producao/receitas/', payload);
  }

  updateRecipe(id: number, payload: Partial<Recipe>): Observable<Recipe> {
    return this.http.patch<Recipe>(`/api/producao/receitas/${id}/`, payload);
  }

  getOrders(): Observable<Order[]> {
    return this.list<Order>('/api/pedido/');
  }

  createOrder(payload: OrderCreationPayload): Observable<Order> {
    return this.http.post<Order>('/api/pedido/', payload);
  }

  updateOrder(id: number, payload: OrderCreationPayload | Partial<Order>): Observable<Order> {
    return this.http.patch<Order>(`/api/pedido/${id}/`, payload);
  }

  analyzeProduction(orderId: number): Observable<ProductionAnalysis> {
    return this.http.post<ProductionAnalysis>(`/api/producao/pedidos/${orderId}/validar/`, {});
  }

  startProduction(orderId: number): Observable<Order> {
    return this.http.post<Order>(`/api/producao/pedidos/${orderId}/iniciar/`, {});
  }

  completeProduction(
    orderId: number,
    payload: CompleteProductionPayload,
  ): Observable<{ pedido: Order; custo_producao: string }> {
    return this.http.post<{ pedido: Order; custo_producao: string }>(
      `/api/producao/pedidos/${orderId}/concluir/`,
      payload,
    );
  }

  cancelOrder(orderId: number, payload: CancelOrderPayload): Observable<unknown> {
    return this.http.post(`/api/pedido/${orderId}/cancelar/`, payload);
  }

  consumeStock(orderId: number): Observable<Order> {
    return this.http.post<Order>(`/api/pedido/${orderId}/consumir-estoque/`, {});
  }

  finishInternalOrder(orderId: number): Observable<Order> {
    return this.http.post<Order>(`/api/pedido/${orderId}/concluir/`, {});
  }

  private list<T>(url: string): Observable<T[]> {
    return this.http
      .get<ApiCollection<T>>(url)
      .pipe(map((response) => (Array.isArray(response) ? response : response.results)));
  }
}
