import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
	selector: 'app-login',
	standalone: true,
	imports: [ReactiveFormsModule],
	templateUrl: './login.component.html',
	styleUrls: ['./login.component.scss'],
})
export class LoginComponent {
	private fb = inject(NonNullableFormBuilder);
	private authService = inject(AuthService);
	private router = inject(Router);

	readonly loading = signal(false);
	readonly errorMessage = signal<string | null>(null);

	readonly form = this.fb.group({
		username: ['', [Validators.required]],
		password: ['', [Validators.required, Validators.minLength(6)]],
	});

	onSubmit() {
		if (this.form.invalid) return;

		this.loading.set(true);
		this.errorMessage.set(null);

		this.authService.login(this.form.getRawValue()).subscribe({
			next: () => this.router.navigate(['/dashboard']),
			error: (err) => {
				this.errorMessage.set(err.error?.message || 'An error occurred during login.');
				this.loading.set(false);
			},
		});
	}
}