import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {UserGlobalStore} from '../../store/user_global_store';

/** Component that displays executed Flows on the currently selected Client. */
@Component({
  standalone: false,
  selector: 'user-menu',
  templateUrl: './user_menu.ng.html',
  styleUrls: ['./user_menu.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserMenu {
  readonly currentUsername$: Observable<string>;

  constructor(private readonly userGlobalStore: UserGlobalStore) {
    this.currentUsername$ = this.userGlobalStore.currentUser$.pipe(
      map((user) => user.name),
    );
  }
}
