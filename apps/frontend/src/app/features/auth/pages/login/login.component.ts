import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';
import { InputTextComponent } from '../../../../shared/components/input-text/input-text.component';
import { LoginHeaderComponent } from '../../components/login-header/login-header.component';
import { LoginFooterComponent } from '../../components/login-footer/login-footer.component';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, InputTextComponent, LoginHeaderComponent, LoginFooterComponent],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent implements OnInit, OnDestroy {
  private fb = inject(NonNullableFormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);

  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);

  currentTime = '';
  private clockInterval: ReturnType<typeof setInterval> | null = null;

  readonly form = this.fb.group({
    login: ['', [Validators.required]],
    senha: ['', [Validators.required, Validators.minLength(6)]],
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

  onSubmit() {
    if (this.form.invalid) return;

    this.loading.set(true);
    this.errorMessage.set(null);

    this.authService.login(this.form.getRawValue()).subscribe({
      next: () =>
        this.router.navigate([
          this.authService.user()?.primeiro_acesso ? '/auth/alterar-senha' : '/dashboard',
        ]),
      error: (err) => {
        this.errorMessage.set(err.error?.detail || 'Não foi possível entrar.');
        this.loading.set(false);
      },
    });
  }
}
