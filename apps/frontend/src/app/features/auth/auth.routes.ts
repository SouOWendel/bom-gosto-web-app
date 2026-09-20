import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';

export const AUTH_ROUTES: Routes = [
	{
		path: 'login',
		loadComponent: () => import('./pages/login/login.component').then((m) => m.LoginComponent),
	},
	{
		path: 'alterar-senha',
		loadComponent: () => import('./pages/change-password/change-password.component').then((m) => m.ChangePasswordComponent),
		canActivate: [authGuard],
	},
	{
		path: '',
		redirectTo: 'login',
		pathMatch: 'full',
	}
]