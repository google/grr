import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {BehaviorSubject} from 'rxjs';

import {DateTime} from '../../../lib/date_time';
import {Hunt, HuntState} from '../../../lib/models/hunt';

/** Chip that shows the state of a hunt. */
@Component({
  selector: 'app-hunt-status-chip',
  templateUrl: './hunt_status_chip.ng.html',
  styleUrls: ['./hunt_status_chip.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntStatusChip {
  protected readonly HuntState = HuntState;

  protected readonly hunt$ = new BehaviorSubject<Hunt|null>(null);

  @Input()
  set hunt(hunt: Hunt|null) {
    this.hunt$.next(hunt ?? null);
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
