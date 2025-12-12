import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDividerModule} from '@angular/material/divider';
import {MatMenuModule} from '@angular/material/menu';
import {MatSlideToggleModule} from '@angular/material/slide-toggle';

import {GlobalStore} from '../../store/global_store';
import {User} from '../shared/user';

/** User menu component. */
@Component({
  selector: 'user-menu',
  templateUrl: './user_menu.ng.html',
  styleUrls: ['./user_menu.scss'],
  imports: [
    CommonModule,
    MatButtonModule,
    MatDividerModule,
    MatMenuModule,
    MatSlideToggleModule,
    User,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserMenu {
  protected readonly globalStore = inject(GlobalStore);

  darkMode = false;

  protected readonly username = computed(
    () => this.globalStore.currentUser()?.name,
  );

  constructor() {
    this.setDarkMode(
      (window.localStorage.getItem('darkMode') || 'false') === 'true',
    );
  }

  setDarkMode(darkMode: boolean) {
    this.darkMode = darkMode;

    if (darkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }

    window.localStorage.setItem('darkMode', darkMode.toString());
  }
}
