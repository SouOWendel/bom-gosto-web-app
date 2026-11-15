import { Component, input, output, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import {
  LucideDynamicIcon,
  LucideEllipsisVertical,
  LucideUser,
  LucideLogOut,
  LucideCakeSlice,
  provideLucideIcons,
  LucideLayoutGrid,
  LucideReceipt,
  LucideArchive,
  LucideChartColumn,
  LucideShoppingBag,
} from '@lucide/angular';
import { DEFAULT_SIDEBAR_PAGES, NavItem, UserProfile } from './sidebar.model';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [
    RouterLink,
    RouterLinkActive,
    LucideDynamicIcon,
    LucideEllipsisVertical,
    LucideUser,
    LucideLogOut,
    LucideCakeSlice,
  ],
  providers: [
    provideLucideIcons(
      LucideLayoutGrid,
      LucideReceipt,
      LucideCakeSlice,
      LucideArchive,
      LucideChartColumn,
      LucideEllipsisVertical,
      LucideUser,
      LucideLogOut,
      LucideShoppingBag,
    ),
  ],
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss'],
})
export class SidebarComponent {
  /**
   * Lista de itens do menu de navegação.
   * Por padrão, carrega as páginas padrão da aplicação.
   */
  readonly items = input<NavItem[]>(DEFAULT_SIDEBAR_PAGES);

  /**
   * Informações do usuário exibidas no rodapé da sidebar.
   */
  readonly user = input<UserProfile>({
    name: 'Chef Rosangela',
    role: 'Head Confeiteira',
  });

  readonly brandTitle = input<string>('Bom Gosto');
  readonly brandSubtitle = input<string>('BOLOS & DOCES');

  readonly logout = output<void>();
  readonly itemClick = output<NavItem>();

  readonly isUserMenuOpen = signal<boolean>(false);

  /** Em telas até 1024px a sidebar vira um menu lateral aberto pela topbar. */
  readonly mobileOpen = input<boolean>(false);

  toggleUserMenu(event?: Event): void {
    event?.stopPropagation();
    this.isUserMenuOpen.update((open) => !open);
  }

  closeUserMenu(): void {
    this.isUserMenuOpen.set(false);
  }

  handleLogout(): void {
    this.closeUserMenu();
    this.logout.emit();
  }

  onItemClick(item: NavItem): void {
    this.itemClick.emit(item);
  }
}
