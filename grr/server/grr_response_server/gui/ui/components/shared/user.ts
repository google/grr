import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';

import {GlobalStore} from '../../store/global_store';

/** Displays a user's profile image or fallback icon, optionally with the username. */
@Component({
  selector: 'user',
  templateUrl: './user.ng.html',
  styleUrls: ['./user.scss'],
  imports: [CommonModule, MatIconModule, MatTooltipModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class User {
  private readonly globalStore = inject(GlobalStore);

  readonly username = input.required<string | undefined>();
  readonly size = input<string>();
  // It true the username will be displayed next to the image.
  readonly withName = input<boolean>(false);

  readonly url = computed(() => {
    const profileImageUrl = this.globalStore.uiConfig()?.profileImageUrl;
    if (!profileImageUrl) return undefined;

    const username = this.username();
    if (!username) return undefined;

    return profileImageUrl.replace('{username}', encodeURIComponent(username));
  });
}
