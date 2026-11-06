import { Component, HostListener, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  LucideAlertTriangle,
  LucideInfo,
  LucideLockKeyhole,
  LucidePackage,
  LucideTrash2,
  LucideX,
  LucideDynamicIcon,
  provideLucideIcons,
} from '@lucide/angular';
import { InputTextComponent } from '../input-text/input-text.component';
import { ButtonComponent } from '../button/button.component';

interface Ingredient {
  name: string;
  quantity: string;
  observation: string;
}

@Component({
  selector: 'app-cancel-production-modal',
  standalone: true,
  imports: [FormsModule, InputTextComponent, ButtonComponent, LucideDynamicIcon],
  providers: [
    provideLucideIcons(
      LucideAlertTriangle,
      LucideInfo,
      LucideLockKeyhole,
      LucidePackage,
      LucideTrash2,
      LucideX,
    ),
  ],
  templateUrl: './cancel-production-modal.component.html',
  styleUrls: ['./cancel-production-modal.component.scss'],
})
export class CancelProductionModalComponent {
  reuseProductName = 'Brownie de cacau reaproveitado';
  reuseQuantity = '12';
  reuseExpiration = '2026-10-30';
  reuseCost = '45,00';
  reusePrice = '60,00';

  readonly closed = output<void>();
  readonly confirmed = output<void>();

  readonly ingredients: Ingredient[] = [
    { name: 'Chocolate Belga 70%', quantity: '400', observation: '400 g utilizados' },
    { name: 'Manteiga sem sal', quantity: '200', observation: '200 g utilizados' },
    { name: 'Açúcar cristal', quantity: '300', observation: '300 g utilizados' },
    { name: 'Ovos grandes', quantity: '4', observation: '4 unidades utilizadas' },
    { name: 'Farinha de trigo', quantity: '200', observation: '200 g utilizados' },
    { name: 'Cacau em pó', quantity: '100', observation: '100 g utilizados' },
  ];

  selectedDestination: 'stock' | 'discard' = 'stock';

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  close(): void {
    this.closed.emit();
  }

  confirm(): void {
    this.confirmed.emit();
  }
}
