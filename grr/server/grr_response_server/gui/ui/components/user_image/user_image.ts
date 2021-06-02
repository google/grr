import {ChangeDetectionStrategy, Component, Input, OnChanges, SimpleChanges} from '@angular/core';
import {combineLatest, ReplaySubject} from 'rxjs';
import {map} from 'rxjs/operators';

import {ConfigGlobalStore} from '../../store/config_global_store';

/** Displays a user's profile image or fallback icon. */
@Component({
  selector: 'user-image',
  templateUrl: './user_image.ng.html',
  styleUrls: ['./user_image.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserImage implements OnChanges {
  @Input() username?: string;

  @Input() size?: string;

  readonly username$ = new ReplaySubject<string|undefined>(1);

  private readonly userImageUrl$ = this.configGlobalStore.uiConfig$.pipe(
      map(uiConfig => uiConfig.profileImageUrl),
  );

  readonly url$ = combineLatest([
                    this.username$, this.userImageUrl$
                  ]).pipe(map(([username, userImageUrl]) => {
    if (!username || !userImageUrl) {
      return undefined;
    } else {
      return userImageUrl.replace('{username}', encodeURIComponent(username));
    }
  }));

  constructor(private readonly configGlobalStore: ConfigGlobalStore) {}

  ngOnChanges(changes: SimpleChanges) {
    this.username$.next(this.username);
  }
}
