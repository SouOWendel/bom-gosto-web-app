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
		// canActivate: [authGuard],
		children: [
			{
				path: 'inicio',
				title: 'Dashboard - Bom Gosto',
				loadComponent: () =>
					import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
			},
			{
				path: 'pedidos',
				title: 'Orders - Bom Gosto',
				loadComponent: () =>
					import('./features/orders/orders.component').then((m) => m.OrdersComponent),
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

