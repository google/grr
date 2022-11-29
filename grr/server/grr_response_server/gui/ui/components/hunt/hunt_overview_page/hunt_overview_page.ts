import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, TrackByFunction} from '@angular/core';
import {MatCardModule} from '@angular/material/card';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {RouterModule} from '@angular/router';
import {Observable} from 'rxjs';

import {Hunt, HuntState} from '../../../lib/models/hunt';
import {HuntOverviewPageLocalStore} from '../../../store/hunt_overview_page_local_store';
import {InfiniteListModule} from '../../helpers/infinite_list/infinite_list_module';
import {TimestampModule} from '../../timestamp/module';
import {UserImageModule} from '../../user_image/module';

/** Page showing an overview of recent hunts. */
@Component({
  selector: 'app-hunt-overview-page',
  templateUrl: './hunt_overview_page.ng.html',
  styleUrls: ['./hunt_overview_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [HuntOverviewPageLocalStore],
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule,
    InfiniteListModule,
    TimestampModule,
    UserImageModule,
  ],
  standalone: true,
})
export class HuntOverviewPage {
  protected readonly HuntState = HuntState;

  protected readonly hunts$: Observable<readonly Hunt[]> =
      this.huntOverviewPageLocalStore.results$;

  constructor(protected readonly huntOverviewPageLocalStore:
                  HuntOverviewPageLocalStore) {
    huntOverviewPageLocalStore.setArgs({});
  }

  readonly trackHuntById: TrackByFunction<Hunt> = (index, item) => item.huntId;

  getHuntProgressMax(hunt: Hunt): number {
    const allClientsCount = Number(hunt.allClientsCount);
    const clientLimit = Number(hunt.safetyLimits.clientLimit);

    if (!this.isRunning(hunt)) {
      // If the hunt is not running, the progress bar spans all scheduled
      // clients.
      return allClientsCount;
    } else if (!clientLimit) {
      // If the hunt is running and the client limit is unset (0), the
      // progress bar spans all scheduled clients + a 10% buffer to show
      // the buffering animation indicating the search for more clients.
      return allClientsCount * 1.1;
    } else {
      // If a client limit is set, the progress bar spans the maximum of the
      // client limit and the number of scheduled clients. Due to scheduling
      // race conditions, there can be slightly more scheduled clients than
      // the client limit.
      return Math.max(clientLimit, allClientsCount);
    }
  }

  /** Returns the percentage of completed clients. */
  getHuntProgress(hunt: Hunt): number {
    const max = this.getHuntProgressMax(hunt);
    if (max) {
      // If a maximum client number can be determined, report the progress
      // of completed clients as a percentage of the maximum number.
      return (Number(hunt.completedClientsCount) / max) * 100;
    } else if (this.isRunning(hunt)) {
      // If no maximum can be reported (yet) and the hunt is running,
      // report a progress of 0.
      return 0;
    } else {
      // If no maximum can be reported and the hunt is no longer running,
      // report a progress of 100 %.
      return 100;
    }
  }

  /** Returns the percentage of scheduled clients. */
  getHuntBufferProgress(hunt: Hunt): number {
    const max = this.getHuntProgressMax(hunt);
    return !max ? 0 : (Number(hunt.allClientsCount) / max) * 100;
  }

  getHuntProgressTooltip(hunt: Hunt): string {
    switch (hunt.state) {
      case HuntState.COMPLETED:
        return 'Completed';
      case HuntState.STOPPED:
        return 'Stopped';
      case HuntState.PAUSED:
        return 'Paused';
      default:
        return 'Waiting for clients';
    }
  }

  isRunning(hunt: Hunt) {
    return hunt.state === HuntState.STARTED;
  }
}
