import { Component, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
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
  LucideTrendingUp,
  LucideBanknote,
  LucideChartColumn,
  LucideSettings,
  LucideCircle,
} from '@lucide/angular';
import { DEFAULT_SIDEBAR_PAGES, NavItem, UserProfile } from './sidebar.model';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [
    CommonModule,
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
      LucideTrendingUp,
      LucideBanknote,
      LucideChartColumn,
      LucideSettings,
      LucideEllipsisVertical,
      LucideUser,
      LucideLogOut,
      LucideCircle,
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
  readonly profileClick = output<void>();

  readonly isUserMenuOpen = signal<boolean>(false);
  readonly isMobileOpen = signal<boolean>(false);

  /**
   * Converte apelidos amigáveis para os identificadores oficiais do Lucide
   */
  getIconName(icon: string): string {
    const aliasMap: Record<string, string> = {
      dashboard: 'layout-grid',
      inicio: 'layout-grid',
      pedidos: 'receipt',
      produtos: 'cake-slice',
      estoque: 'archive',
      inventario: 'chart-column',
    };
    return aliasMap[icon] ?? icon;
  }

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
    this.closeMobile();
    this.itemClick.emit(item);
  }

  onProfileClick(): void {
    this.closeUserMenu();
    this.profileClick.emit();
  }

  toggleMobile(): void {
    this.isMobileOpen.update((open) => !open);
  }

  closeMobile(): void {
    this.isMobileOpen.set(false);
  }
}
