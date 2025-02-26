import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  TrackByFunction,
} from '@angular/core';
import {FormControl} from '@angular/forms';
import {Router} from '@angular/router';
import {Observable, combineLatest} from 'rxjs';
import {map, startWith, takeUntil, tap} from 'rxjs/operators';

import {
  ApiHuntState,
  ApiListHuntsArgsRobotFilter,
} from '../../../lib/api/api_interfaces';
import {Hunt, HuntState, getHuntTitle} from '../../../lib/models/hunt';
import {observeOnDestroy} from '../../../lib/reactive';
import {HuntOverviewPageLocalStore} from '../../../store/hunt_overview_page_local_store';
import {ColorScheme} from '../../flow_details/helpers/result_accordion';

/** Hunt creator filter enum used for classifying the hunts. */
export enum HuntCreatorFilter {
  ALL_HUMAN_HUNTS = 'All human fleet collections',
  ALL_ROBOT_HUNTS = 'All robot fleet collections',
  ALL_HUNTS = 'All fleet collections',
}

function toRobotFilter(
  creatorFilter: HuntCreatorFilter,
): ApiListHuntsArgsRobotFilter {
  switch (creatorFilter) {
    case HuntCreatorFilter.ALL_HUMAN_HUNTS:
      return ApiListHuntsArgsRobotFilter.NO_ROBOTS;
    case HuntCreatorFilter.ALL_ROBOT_HUNTS:
      return ApiListHuntsArgsRobotFilter.ONLY_ROBOTS;
    default:
      return ApiListHuntsArgsRobotFilter.UNKNOWN;
  }
}

/** Hunt state filter enum used for classifying the hunts. */
export enum HuntStateFilter {
  ANY = 'Any',
  NOT_STARTED = 'Not started',
  PAUSED = 'Paused',
  RUNNING = 'Running',
  CANCELLED = 'Cancelled',
  COMPLETED = 'Completed',
}

function toApiHuntState(state: HuntStateFilter): ApiHuntState | undefined {
  switch (state) {
    case HuntStateFilter.NOT_STARTED:
      return ApiHuntState.PAUSED;
    case HuntStateFilter.PAUSED:
      return ApiHuntState.PAUSED;
    case HuntStateFilter.RUNNING:
      return ApiHuntState.STARTED;
    case HuntStateFilter.CANCELLED:
      return ApiHuntState.STOPPED;
    case HuntStateFilter.COMPLETED:
      return ApiHuntState.COMPLETED;
    default:
      return undefined;
  }
}

/** Page showing an overview of recent hunts. */
@Component({
  standalone: false,
  selector: 'app-hunt-overview-page',
  templateUrl: './hunt_overview_page.ng.html',
  styleUrls: ['./hunt_overview_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [HuntOverviewPageLocalStore],
})
export class HuntOverviewPage implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);
  protected readonly ColorScheme = ColorScheme;
  protected readonly HuntCreatorFilter = HuntCreatorFilter;
  protected readonly HuntStateFilter = HuntStateFilter;
  protected readonly getHuntTitle = getHuntTitle;

  protected readonly huntCreatorDefault = HuntCreatorFilter.ALL_HUMAN_HUNTS;
  readonly huntCreatorFilterForm = new FormControl(this.huntCreatorDefault);
  protected readonly huntStateDefault = HuntStateFilter.ANY;
  readonly huntStateFilterForm = new FormControl(this.huntStateDefault);

  protected readonly hunts$: Observable<readonly Hunt[]>;

  constructor(
    protected readonly huntOverviewPageLocalStore: HuntOverviewPageLocalStore,
    private readonly router: Router,
  ) {
    this.hunts$ = this.huntOverviewPageLocalStore.results$.pipe(
      map((hunts) =>
        hunts.filter((hunt) => {
          // We need this filter on top because hunt states in the backend
          // and frontend don't correspond to each other. Thus, if the user
          // selected `NOT_STARTED`, we will have both `NOT_STARTED` and
          // `PAUSED` in the results.
          switch (this.huntStateFilterForm.value) {
            case HuntStateFilter.NOT_STARTED:
              return hunt.state === HuntState.NOT_STARTED;
            case HuntStateFilter.PAUSED:
              return hunt.state === HuntState.REACHED_CLIENT_LIMIT;
            case HuntStateFilter.RUNNING:
              return hunt.state === HuntState.RUNNING;
            case HuntStateFilter.CANCELLED:
              return hunt.state === HuntState.CANCELLED;
            case HuntStateFilter.COMPLETED:
              return hunt.state === HuntState.REACHED_TIME_LIMIT;
            default:
              return true;
          }
        }),
      ),
    );
    this.trackHuntById = (index, item) => item.huntId;
    huntOverviewPageLocalStore.setArgs({
      robotFilter: ApiListHuntsArgsRobotFilter.NO_ROBOTS,
    });

    combineLatest([
      this.huntCreatorFilterForm.valueChanges.pipe(
        startWith(this.huntCreatorDefault),
      ),
      this.huntStateFilterForm.valueChanges.pipe(
        startWith(this.huntStateDefault),
      ),
    ])
      .pipe(
        takeUntil(this.ngOnDestroy.triggered$),
        tap(([creatorFilter, stateFilter]) => {
          const args: {
            robotFilter?: ApiListHuntsArgsRobotFilter;
            withState?: ApiHuntState;
          } = {};
          if (creatorFilter) {
            args.robotFilter = toRobotFilter(creatorFilter);
          }
          if (stateFilter) {
            const translatedState = toApiHuntState(stateFilter);
            if (translatedState) {
              args.withState = translatedState;
            }
          }
          huntOverviewPageLocalStore.setArgs(args);
        }),
      )
      .subscribe();
  }

  readonly trackHuntById: TrackByFunction<Hunt>;

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
      case HuntState.REACHED_TIME_LIMIT:
        return 'Completed';
      case HuntState.CANCELLED:
        return 'Cancelled';
      case HuntState.NOT_STARTED:
        return 'Not started';
      case HuntState.REACHED_CLIENT_LIMIT:
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

  duplicateHunt(huntId: string) {
    this.router.navigate(['/new-hunt'], {queryParams: {'huntId': huntId}});
  }
}
