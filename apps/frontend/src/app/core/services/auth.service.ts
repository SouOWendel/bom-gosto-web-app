import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap } from 'rxjs';
import { AuthResponse, Credentials, User } from '../models/auth.model';

@Injectable({
	providedIn: 'root',
})
export class AuthService {
	private http = inject(HttpClient);
	
	// Readonly signals to hold the user state and authentication status
	readonly user = signal<User | null>(null);
	readonly isAuthenticated = computed(() => !!this.user());

	login(credencials: Credentials) {
		return this.http.post<AuthResponse>('/api/auth/login', credencials).pipe(
			tap((response) => {
				localStorage.setItem('access_token', response.access);
				this.user.set(response.user);
			})
		)
	}

	logout(): void {
		localStorage.removeItem('access_token');
		this.user.set(null);
	}
}
