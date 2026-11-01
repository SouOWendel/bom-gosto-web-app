import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { MainLayoutComponent } from './core/layout/main-layout.component';

export const routes: Routes = [
	{
		path: 'auth',
		loadChildren: () => import('./features/auth/auth.routes').then((m) => m.AUTH_ROUTES),
	},
	{
		path: '',
		component: MainLayoutComponent,
		// TODO: descomentar o guard de autenticação
		// canActivate: [authGuard], 
		children: [
			{
				path: 'inicio',
				title: 'Início - Bom Gosto',
				loadComponent: () =>
					import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
			},
			{
				path: 'pedidos',
				title: 'Pedidos - Bom Gosto',
				loadComponent: () =>
					import('./features/orders/orders.component').then((m) => m.OrdersComponent),
			},
			{
				path: 'produtos',
				title: 'Produtos - Bom Gosto',
				loadComponent: () =>
					import('./features/products/products.component').then((m) => m.ProductsComponent),
			},
			{
				path: 'estoque',
				title: 'Estoque - Bom Gosto',
				loadComponent: () =>
					import('./features/stock/stock.component').then((m) => m.StockComponent),
			},
			{
				path: 'inventario',
				title: 'Inventário - Bom Gosto',
				loadComponent: () =>
					import('./features/inventory/inventory.component').then((m) => m.InventoryComponent),
			},
			{
				path: '',
				redirectTo: 'inicio',
				pathMatch: 'full',
			},
		],
	},
	{
		path: '**',
		redirectTo: 'auth/login',
	},
];

