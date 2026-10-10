import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { DashboardComponent } from './features/dashboard/dashboard.component';

export const routes: Routes = [
	{
		path: 'auth',
		loadChildren: () => import('./features/auth/auth.routes').then((m) => m.AUTH_ROUTES),
	},
	{
		path: 'dashboard',
		component: DashboardComponent,
		canActivate: [authGuard],
	},
	{
		path: '',
		redirectTo: 'auth/login',
		pathMatch: 'full'
	},
	{
		path: '**',
		redirectTo: 'auth/login',
	}
];
