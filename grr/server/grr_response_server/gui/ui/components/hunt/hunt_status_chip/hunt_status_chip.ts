import {ChangeDetectionStrategy, Component, Input, OnDestroy} from '@angular/core';
import {BehaviorSubject} from 'rxjs';
import {tap} from 'rxjs/operators';

import {DateTime} from '../../../lib/date_time';
import {Hunt, HuntState} from '../../../lib/models/hunt';
import {GrrUser} from '../../../lib/models/user';
import {observeOnDestroy} from '../../../lib/reactive';
import {UserGlobalStore} from '../../../store/user_global_store';

const APPROVAL_NOT_REQUIRED_NOT_STARTED_TOOLTOP =
    'This hunt has never been started.';
const APPROVAL_REQUIRED_NOT_STARTED_TOOLTOP =
    'Either the hunt has no approval, or it was never started after approval was granted.';
const CANCELLED_BY_USER_TOOLTIP = 'Cancelled by user';


/** Chip that shows the state of a hunt. */
@Component({
  selector: 'app-hunt-status-chip',
  templateUrl: './hunt_status_chip.ng.html',
  styleUrls: ['./hunt_status_chip.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntStatusChip implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);
  protected readonly HuntState = HuntState;

  protected readonly hunt$ = new BehaviorSubject<Hunt|null>(null);

  protected notStartedTooltip = APPROVAL_NOT_REQUIRED_NOT_STARTED_TOOLTOP;

  @Input()
  set hunt(hunt: Hunt|null) {
    this.hunt$.next(hunt ?? null);
  }

  protected readonly huntApprovalRequired$ =
      this.userGlobalStore.currentUser$.pipe();

  constructor(private readonly userGlobalStore: UserGlobalStore) {
    this.userGlobalStore.currentUser$
        .pipe(
            tap((user: GrrUser) => {
              if (user.huntApprovalRequired) {
                this.notStartedTooltip = APPROVAL_REQUIRED_NOT_STARTED_TOOLTOP;
              } else {
                this.notStartedTooltip =
                    APPROVAL_NOT_REQUIRED_NOT_STARTED_TOOLTOP;
              }
            }),
            )
        .subscribe();
  }

  get cancelledTooltip() {
    // Hunts cancelled in the UI prior to cl/ had an empty comment.
    if (this.hunt$.getValue()?.stateComment) {
      return this.hunt$.getValue()?.stateComment!;
    }
    return CANCELLED_BY_USER_TOOLTIP;
  }

  get timeUntilExpiry() {
    const hunt = this.hunt$.getValue();

    if (!hunt || !hunt.initStartTime || !hunt.duration) {
      return '';
    }

    const initTime = DateTime.fromJSDate(hunt.initStartTime);
    const expiryTime = initTime.plus(hunt.duration);

    // TODO: Some hunts are not marked as complete even if the
    // expiry time is in the past. This is a workaround until this is fixed.
    if (expiryTime < DateTime.now()) {
      return '';
    }

    return ` –  ${expiryTime.toRelative()!.replace('in ', '')} left`;
  }
}
