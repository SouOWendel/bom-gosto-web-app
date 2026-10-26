import { Component, computed, inject } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar.component';
import { UserProfile } from '../../shared/components/sidebar/sidebar.model';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [RouterOutlet, SidebarComponent],
  templateUrl: './main-layout.component.html',
  styleUrls: ['./main-layout.component.scss'],
})
export class MainLayoutComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

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
    this.authService.logout().subscribe(() => {
      this.router.navigate(['/auth/login']);
    });
  }
}
