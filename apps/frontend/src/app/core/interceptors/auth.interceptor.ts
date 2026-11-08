import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { switchMap } from 'rxjs';
import { CsrfService } from '../services/csrf.service';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const authenticatedRequest = request.clone({ withCredentials: true });
  if (['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(request.method)) {
    return next(authenticatedRequest);
  }

  return inject(CsrfService)
    .ensureToken()
    .pipe(
      switchMap((token) =>
        next(
          authenticatedRequest.clone({
            setHeaders: { 'X-CSRFToken': token },
          }),
        ),
      ),
    );
};