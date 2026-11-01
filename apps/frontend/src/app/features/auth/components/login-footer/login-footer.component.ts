import { Component } from '@angular/core';

@Component({
  selector: 'app-login-footer',
  standalone: true,
  templateUrl: './login-footer.component.html',
  styleUrls: ['./login-footer.component.scss'],
})
export class LoginFooterComponent {
  readonly currentYear = new Date().getFullYear();
}
