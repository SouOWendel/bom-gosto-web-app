import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { ChangePasswordComponent } from './change-password.component';
import { AuthService } from '../../../../core/services/auth.service';

describe('ChangePasswordComponent', () => {
  let component: ChangePasswordComponent;
  let fixture: ComponentFixture<ChangePasswordComponent>;
  let authServiceSpy: {
    user: { update: ReturnType<typeof vi.fn> };
    changePassword: ReturnType<typeof vi.fn>;
    logout: ReturnType<typeof vi.fn>;
  };
  let routerSpy: {
    navigate: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    authServiceSpy = {
      user: { update: vi.fn() },
      changePassword: vi.fn(),
      logout: vi.fn().mockReturnValue(of(undefined)),
    };
    routerSpy = {
      navigate: vi.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [ChangePasswordComponent],
      providers: [
        { provide: AuthService, useValue: authServiceSpy },
        { provide: Router, useValue: routerSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ChangePasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the component and initialize clock', () => {
    expect(component).toBeTruthy();
    expect(component.currentTime).toMatch(/^\d{2}:\d{2}$/);
    expect(component.form.valid).toBe(false);
  });

  it('should invalidate form if new password has less than 8 characters', () => {
    component.form.patchValue({
      currentPassword: 'old-password',
      newPassword: 'short',
      confirmation: 'short',
    });

    expect(component.form.valid).toBe(false);
    expect(component.form.get('newPassword')?.hasError('minlength')).toBe(true);
  });

  it('should show error when new password is identical to temporary password', () => {
    component.form.patchValue({
      currentPassword: 'password123',
      newPassword: 'password123',
      confirmation: 'password123',
    });

    component.onSubmit();

    expect(component.errorMessage()).toBe(
      'A nova senha deve ser diferente da senha temporária atual.',
    );
    expect(authServiceSpy.changePassword).not.toHaveBeenCalled();
  });

  it('should show error when confirmation does not match new password', () => {
    component.form.patchValue({
      currentPassword: 'old-password123',
      newPassword: 'new-password456',
      confirmation: 'different-password789',
    });

    component.onSubmit();

    expect(component.errorMessage()).toBe('A confirmação da nova senha não confere.');
    expect(authServiceSpy.changePassword).not.toHaveBeenCalled();
  });

  it('should submit successfully and navigate to dashboard', () => {
    authServiceSpy.changePassword.mockReturnValue(
      of({ detail: 'senha alterada com sucesso.', primeiro_acesso: false }),
    );

    component.form.patchValue({
      currentPassword: 'temp-password123',
      newPassword: 'new-strong-password123',
      confirmation: 'new-strong-password123',
    });

    component.onSubmit();

    expect(authServiceSpy.changePassword).toHaveBeenCalledWith(
      'temp-password123',
      'new-strong-password123',
    );
    expect(authServiceSpy.user.update).toHaveBeenCalled();
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/inicio']);
  });

  it('should handle API error on submit', () => {
    authServiceSpy.changePassword.mockReturnValue(
      throwError(() => ({ error: { detail: 'Senha atual incorreta.' } })),
    );

    component.form.patchValue({
      currentPassword: 'wrong-password',
      newPassword: 'new-strong-password123',
      confirmation: 'new-strong-password123',
    });

    component.onSubmit();

    expect(component.errorMessage()).toBe('Senha atual incorreta.');
    expect(component.loading()).toBe(false);
  });

  it('should logout and navigate to login on onBackToLogin', () => {
    component.onBackToLogin();

    expect(authServiceSpy.logout).toHaveBeenCalled();
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/auth/login']);
  });
});
