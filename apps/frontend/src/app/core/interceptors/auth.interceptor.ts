import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { CsrfService } from '../services/csrf.service';

// Rotas de autenticação tratam 401/403 por conta própria.
const AUTH_ENDPOINTS = ['/api/auth/'];

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const authService = inject(AuthService);
  const csrfService = inject(CsrfService);
  const authenticatedRequest = request.clone({ withCredentials: true });

  const send = ['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(request.method)
    ? next(authenticatedRequest)
    : csrfService
        .ensureToken()
        .pipe(
          switchMap((token) =>
            next(authenticatedRequest.clone({ setHeaders: { 'X-CSRFToken': token } })),
          ),
        );

  return send.pipe(
    catchError((error: unknown) => {
      // A autenticação por sessão do DRF responde 403 quando a sessão expira.
      if (
        error instanceof HttpErrorResponse &&
        [401, 403].includes(error.status) &&
        !AUTH_ENDPOINTS.some((endpoint) => request.url.includes(endpoint))
      ) {
        authService.handleRejectedSession();
      }
      return throwError(() => error);
    }),
  );
};
