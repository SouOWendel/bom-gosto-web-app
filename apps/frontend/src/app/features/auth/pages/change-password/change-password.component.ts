import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { InputTextComponent } from '../../../../shared/components/input-text/input-text.component';
import { LoginHeaderComponent } from '../../components/login-header/login-header.component';
import { LoginFooterComponent } from '../../components/login-footer/login-footer.component';
import { LucideArrowLeft, LucideArrowRight, LucideClock } from '@lucide/angular';

@Component({
  selector: 'app-change-password',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    InputTextComponent,
    LoginHeaderComponent,
    LoginFooterComponent,
    LucideArrowLeft,
    LucideArrowRight,
    LucideClock,
  ],
  templateUrl: './change-password.component.html',
  styleUrls: ['./change-password.component.scss'],
})
export class ChangePasswordComponent implements OnInit, OnDestroy {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);

  currentTime = '';
  private clockInterval: ReturnType<typeof setInterval> | null = null;

  readonly form = this.fb.group({
    currentPassword: ['', [Validators.required]],
    newPassword: ['', [Validators.required, Validators.minLength(8)]],
    confirmation: ['', [Validators.required]],
  });

  ngOnInit(): void {
    this.updateTime();
    this.clockInterval = setInterval(() => this.updateTime(), 60_000);
  }

  ngOnDestroy(): void {
    if (this.clockInterval) clearInterval(this.clockInterval);
  }

  private updateTime(): void {
    const now = new Date();
    const h = now.getHours().toString().padStart(2, '0');
    const m = now.getMinutes().toString().padStart(2, '0');
    this.currentTime = `${h}:${m}`;
  }

  onBackToLogin(): void {
    this.authService.logout().subscribe({
      next: () => this.router.navigate(['/auth/login']),
      error: () => this.router.navigate(['/auth/login']),
    });
  }

  onSubmit(): void {
    if (this.form.invalid) return;

    const { currentPassword, newPassword, confirmation } = this.form.getRawValue();

    if (newPassword === currentPassword) {
      this.errorMessage.set('A nova senha deve ser diferente da senha temporária atual.');
      return;
    }

    if (newPassword !== confirmation) {
      this.errorMessage.set('A confirmação da nova senha não confere.');
      return;
    }

    this.loading.set(true);
    this.errorMessage.set(null);

    this.authService.changePassword(currentPassword, newPassword).subscribe({
      next: () => {
        this.authService.user.update((user) => (user ? { ...user, primeiro_acesso: false } : user));
        this.router.navigate(['/dashboard']);
      },
      error: (error) => {
        this.errorMessage.set(error.error?.detail || 'Não foi possível alterar a senha.');
        this.loading.set(false);
      },
    });
  }
}
