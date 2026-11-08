import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (route: ActivatedRouteSnapshot) => {
	const authService = inject(AuthService);
	const router = inject(Router);

	return authService.checkSession().pipe(
		map((isAuthenticated) => {
			if (!isAuthenticated) {
				return router.createUrlTree(['/auth/login']);
			}

			const firstAccess = authService.user()?.primeiro_acesso;
			const isPasswordRoute = ['alterar-senha', 'primeiro-acesso'].includes(
				route.routeConfig?.path ?? '',
			);
			if (firstAccess && !isPasswordRoute) {
				return router.createUrlTree(['/auth/alterar-senha']);
			}
			if (!firstAccess && isPasswordRoute) {
				return router.createUrlTree(['/inicio']);
			}
			return true;
		}),
	);
};