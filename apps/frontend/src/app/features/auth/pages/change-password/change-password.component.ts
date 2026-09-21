import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { InputTextComponent } from '../../../../shared/components/input-text/input-text.component';

@Component({
  selector: 'app-change-password',
  standalone: true,
  imports: [ReactiveFormsModule, InputTextComponent],
  templateUrl: './change-password.component.html',
  styleUrls: ['./change-password.component.scss'],
})
export class ChangePasswordComponent {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly form = this.fb.group({
    currentPassword: ['', [Validators.required]],
    newPassword: ['', [Validators.required, Validators.minLength(8)]],
    confirmation: ['', [Validators.required]],
  });

  onSubmit() {
    if (this.form.invalid) return;

    const { currentPassword, newPassword, confirmation } = this.form.getRawValue();
    if (newPassword !== confirmation) {
      this.errorMessage.set('A confirmação da nova senha não confere.');
      return;
    }

    this.loading.set(true);
    this.errorMessage.set(null);

    this.authService.changePassword(currentPassword, newPassword).subscribe({
      next: () => {
        this.authService.user.update((user) => user ? { ...user, primeiro_acesso: false } : user);
        this.router.navigate(['/dashboard']);
      },
      error: (error) => {
        this.errorMessage.set(error.error?.detail || 'Não foi possível alterar a senha.');
        this.loading.set(false);
      },
    });
  }
}
