import { Component } from '@angular/core';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [],
  template: `
    <div class="dashboard-page">
      <header class="dashboard-page__header">
        <div>
          <h1 class="dashboard-page__title">Visão Geral</h1>
          <p class="dashboard-page__subtitle">Hello World</p>
        </div>
      </header>
    </div>
  `,
  styles: [`
    .dashboard-page {
      padding: 2rem;

      &__header {
        margin-bottom: 2rem;
      }

      &__title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #2e1d21;
        margin: 0;
      }

      &__subtitle {
        font-size: 0.95rem;
        color: #826c70;
        margin-top: 0.25rem;
      }
    }
  `],
})
export class DashboardComponent {}