import { Component, inject } from '@angular/core';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  template: `
    <div style="padding: 2rem;">
      <h1>Dashboard</h1>
      <p>Bem-vindo, Usuário!</p>
      <button (click)="authService.logout()">Sair</button>
    </div>
  `
})
export class DashboardComponent {
  readonly authService = inject(AuthService);
}