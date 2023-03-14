import {ChangeDetectionStrategy, Component, OnDestroy, TrackByFunction} from '@angular/core';
import {FormControl} from '@angular/forms';
import {Observable} from 'rxjs';
import {tap} from 'rxjs/operators';

import {ApiListHuntsArgsRobotFilter} from '../../../lib/api/api_interfaces';
import {getHuntTitle, Hunt, HuntState} from '../../../lib/models/hunt';
import {observeOnDestroy} from '../../../lib/reactive';
import {HuntOverviewPageLocalStore} from '../../../store/hunt_overview_page_local_store';
import {ColorScheme} from '../../flow_details/helpers/result_accordion';

/** Hunt filter enum used for classifying the hunts. */
export enum HuntFilter {
  ALL_HUMAN_HUNTS = 'All human fleet collections',
  ALL_ROBOT_HUNTS = 'All robot fleet collections',
  ALL_HUNTS = 'All fleet collections',
}

/** Page showing an overview of recent hunts. */
@Component({
  selector: 'app-hunt-overview-page',
  templateUrl: './hunt_overview_page.ng.html',
  styleUrls: ['./hunt_overview_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [HuntOverviewPageLocalStore],
})
export class HuntOverviewPage implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);
  protected readonly HuntState = HuntState;
  protected readonly ColorScheme = ColorScheme;
  protected readonly HuntFilter = HuntFilter;
  protected readonly getHuntTitle = getHuntTitle;

  readonly huntFiltersForm = new FormControl(HuntFilter.ALL_HUMAN_HUNTS);

  protected readonly hunts$: Observable<readonly Hunt[]> =
      this.huntOverviewPageLocalStore.results$;

  constructor(protected readonly huntOverviewPageLocalStore:
                  HuntOverviewPageLocalStore) {
    huntOverviewPageLocalStore.setArgs(
        {robotFilter: ApiListHuntsArgsRobotFilter.NO_ROBOTS});

    this.huntFiltersForm.valueChanges
        .pipe(tap(filterType => {
          switch (filterType) {
            case HuntFilter.ALL_HUMAN_HUNTS:
              huntOverviewPageLocalStore.setArgs(
                  {robotFilter: ApiListHuntsArgsRobotFilter.NO_ROBOTS});
              break;
            case HuntFilter.ALL_ROBOT_HUNTS:
              huntOverviewPageLocalStore.setArgs(
                  {robotFilter: ApiListHuntsArgsRobotFilter.ONLY_ROBOTS});
              break;
            default:
              huntOverviewPageLocalStore.setArgs(
                  {robotFilter: ApiListHuntsArgsRobotFilter.UNKNOWN});
              break;
          }
        }))
        .subscribe();
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
      case HuntState.CANCELLED:
        return 'Cancelled';
      case HuntState.NOT_STARTED:
        return 'Not started';
      case HuntState.PAUSED:
        return 'Paused';
      default:
        return 'Waiting for clients';
    }
  }

  isRunning(hunt: Hunt) {
    return hunt.state === HuntState.RUNNING;
  }
  huntStarted(hunt: Hunt) {
    return hunt.state !== HuntState.NOT_STARTED;
  }
}
