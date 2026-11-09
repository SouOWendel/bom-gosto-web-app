import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, finalize, map, Observable, of, tap, throwError } from 'rxjs';
import { AuthResponse, ChangePasswordResponse, Credentials, User } from '../models/auth.model';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private revalidating = false;

  // Readonly signals to hold the user state and authentication status
  readonly user = signal<User | null>(null);
  readonly isAuthenticated = computed(() => !!this.user());

  login(credentials: Credentials): Observable<AuthResponse> {
    return this.http.post<AuthResponse>('/api/auth/login/', credentials).pipe(
      tap((response) =>
        this.user.set({
          login: response.login,
          primeiro_acesso: response.primeiro_acesso,
        }),
      ),
    );
  }

  checkSession(): Observable<boolean> {
    if (this.isAuthenticated()) return of(true);

    return this.http.get<User>('/api/auth/me/').pipe(
      tap((user) => this.user.set(user)),
      map(() => true),
      catchError((error: HttpErrorResponse) => {
        if (![401, 403].includes(error.status)) {
          return throwError(() => error);
        }
        this.user.set(null);
        return of(false);
      }),
    );
  }

  changePassword(currentPassword: string, newPassword: string): Observable<ChangePasswordResponse> {
    return this.http.post<ChangePasswordResponse>('/api/auth/alterar-senha/', {
      senha_atual: currentPassword,
      nova_senha: newPassword,
    });
  }

  // Chamado quando a API recusa a sessão: confirma no servidor e redireciona.
  handleRejectedSession(): void {
    if (this.revalidating) return;
    this.revalidating = true;
    this.user.set(null);
    this.checkSession()
      .pipe(finalize(() => (this.revalidating = false)))
      .subscribe({
        next: (isAuthenticated) => {
          if (!isAuthenticated) {
            this.router.navigate(['/auth/login']);
          } else if (this.user()?.primeiro_acesso) {
            this.router.navigate(['/auth/alterar-senha']);
          }
        },
        error: () => undefined,
      });
  }

  logout() {
    return this.http.post<void>('/api/auth/logout/', {}).pipe(finalize(() => this.user.set(null)));
  }
}
