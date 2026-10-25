import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [SidebarComponent],
  template: `
    <div class="dashboard-layout">
      <!-- Menu Lateral -->
      <app-sidebar (logout)="logout()" />

      <!-- Conteúdo Principal -->
      <main class="dashboard-layout__content">
        <header class="dashboard-layout__header">
          <div>
            <h1 class="dashboard-layout__title">Visão Geral</h1>
            <p class="dashboard-layout__subtitle">Hello World</p>
          </div>
        </header>
      </main>
    </div>
  `,
  styles: [`
    .dashboard-layout {
      display: flex;
      min-height: 100vh;
      background-color: #faf5f5;
    }
  `]
})
export class DashboardComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  logout(): void {
    this.authService.logout().subscribe(() => this.router.navigate(['/auth/login']));
  }
}