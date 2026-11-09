import { Component, computed, inject } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar.component';
import {
  DEFAULT_SIDEBAR_PAGES,
  NavItem,
  UserProfile,
} from '../../shared/components/sidebar/sidebar.model';
import { TopbarComponent } from './topbar/topbar.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [RouterOutlet, SidebarComponent, TopbarComponent],
  templateUrl: './main-layout.component.html',
  styleUrls: ['./main-layout.component.scss'],
})
export class MainLayoutComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly sidebarItems: NavItem[] = DEFAULT_SIDEBAR_PAGES;

  readonly userProfile = computed<UserProfile>(() => {
    const user = this.authService.user();
    if (user?.login) {
      return {
        name: user.login,
        role: 'Administrador',
      };
    }
    return {
      name: 'Chef Rosangela',
      role: 'Head Confeiteira',
    };
  });

  onLogout(): void {
    this.authService.logout().subscribe({
      next: () => void this.router.navigate(['/auth/login']),
      error: () => void this.router.navigate(['/auth/login']),
    });
  }
}
