import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { catchError, finalize, map, Observable, of, tap } from 'rxjs';
import { AuthResponse, ChangePasswordResponse, Credentials, User } from '../models/auth.model';

@Injectable({
	providedIn: 'root',
})
export class AuthService {
	private http = inject(HttpClient);
	
	// Readonly signals to hold the user state and authentication status
	readonly user = signal<User | null>(null);
	readonly isAuthenticated = computed(() => !!this.user());

	login(credentials: Credentials) {
		return this.http.post<AuthResponse>('/api/auth/login/', credentials, { withCredentials: true }).pipe(
			tap((response) => this.user.set({
				login: response.login,
				primeiro_acesso: response.primeiro_acesso,
			}))
		);
	}

	checkSession(): Observable<boolean> {
		if (this.isAuthenticated()) return of(true);

		return this.http.get<User>('/api/auth/me/', { withCredentials: true }).pipe(
			tap((user) => this.user.set(user)),
			map(() => true),
			catchError(() => {
				this.user.set(null);
				return of(false);
			}),
		);
	}

	changePassword(currentPassword: string, newPassword: string) {
		return this.http.post<ChangePasswordResponse>('/api/auth/alterar-senha/', {
			senha_atual: currentPassword,
			nova_senha: newPassword,
		}, { withCredentials: true });
	}

	logout() {
		return this.http.post<void>('/api/auth/logout/', {}, { withCredentials: true }).pipe(
			finalize(() => this.user.set(null)),
		);
	}
}
