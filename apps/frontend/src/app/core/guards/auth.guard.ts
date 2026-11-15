import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
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

// Leva quem já tem sessão ativa para dentro do app em vez de exibir o login.
export const guestGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return authService.checkSession().pipe(
    map((isAuthenticated) => {
      if (!isAuthenticated) {
        return true;
      }
      return router.createUrlTree([
        authService.user()?.primeiro_acesso ? '/auth/alterar-senha' : '/inicio',
      ]);
    }),
    catchError(() => of(true)),
  );
};
