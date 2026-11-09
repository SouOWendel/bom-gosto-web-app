import { Component, forwardRef, Input } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import {
  LucideCalendar,
  LucideBanknote,
  LucideDynamicIcon,
  LucideEye,
  LucideEyeOff,
  LucideHash,
  LucideLock,
  LucideMail,
  LucidePackage,
  LucidePhone,
  LucideSearch,
  provideLucideIcons,
} from '@lucide/angular';

@Component({
  selector: 'app-input-text',
  standalone: true,
  imports: [LucideDynamicIcon],
  providers: [
    provideLucideIcons(
      LucideCalendar,
      LucideBanknote,
      LucideEye,
      LucideEyeOff,
      LucideHash,
      LucideLock,
      LucideMail,
      LucidePackage,
      LucidePhone,
      LucideSearch,
    ),
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputTextComponent),
      multi: true,
    },
  ],
  templateUrl: './input-text.component.html',
  styleUrls: ['./input-text.component.scss'],
})
export class InputTextComponent implements ControlValueAccessor {
  @Input({ required: true }) label = '';
  @Input({ required: true }) inputId = '';
  @Input() type = 'text';
  @Input() autocomplete = 'off';
  @Input() placeholder = '';
  @Input() icon = 'mail';
  @Input() suffix = '';
  @Input() size: 'default' | 'compact' = 'default';
  @Input() mask: 'phone' | 'currency' | '' = '';

  value = '';
  disabled = false;
  showPassword = false;

  private onChange: (value: string) => void = () => undefined;
  private onTouched: () => void = () => undefined;

  writeValue(value: string | null): void {
    this.value = this.formatValue(value ?? '');
  }

  registerOnChange(onChange: (value: string) => void): void {
    this.onChange = onChange;
  }

  registerOnTouched(onTouched: () => void): void {
    this.onTouched = onTouched;
  }

  setDisabledState(disabled: boolean): void {
    this.disabled = disabled;
  }

  handleInput(value: string): void {
    this.value = this.formatValue(value);
    this.onChange(this.value);
  }

  handleBlur(): void {
    this.onTouched();
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }

  private formatValue(value: string): string {
    if (this.mask === 'phone') {
      const digits = value.replace(/\D/g, '').slice(0, 11);
      if (digits.length <= 2) return digits;
      if (digits.length <= 7) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
      if (digits.length <= 10) {
        return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
      }
      return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
    }

    if (this.mask === 'currency') {
      const normalized = value.replace(/\D/g, '');
      if (!normalized) return '';
      const amount = Number(normalized) / 100;
      return amount.toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    }

    return value;
  }
}
