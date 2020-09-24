import {ChangeDetectionStrategy, Component, OnInit} from '@angular/core';
import {UserFacade} from '@app/store/user_facade';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

/** Component that displays executed Flows on the currently selected Client. */
@Component({
  selector: 'user-menu',
  templateUrl: './user_menu.ng.html',
  styleUrls: ['./user_menu.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserMenu {
  readonly currentUsername$: Observable<string> =
      this.userFacade.currentUser$.pipe(map(user => user.name));

  constructor(private readonly userFacade: UserFacade) {}
}
