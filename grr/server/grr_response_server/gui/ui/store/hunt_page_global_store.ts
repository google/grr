import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {merge, Observable, of} from 'rxjs';
import {
  distinctUntilChanged,
  filter,
  map,
  shareReplay,
  startWith,
  switchMap,
  tap,
  withLatestFrom,
} from 'rxjs/operators';

import {ApiTypeCount} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {
  RequestStatus,
  RequestStatusType,
  trackRequest,
} from '../lib/api/track_request';
import {translateHunt} from '../lib/api_translation/hunt';
import {PAYLOAD_TYPE_TRANSLATION} from '../lib/api_translation/result';
import {Hunt, HuntState} from '../lib/models/hunt';
import {HuntResultsTableTabConfig, PayloadType} from '../lib/models/result';
import {isNonNull} from '../lib/preconditions';

interface HuntPageState {
  readonly huntId?: string;
  readonly patchHuntRequestStatus?: RequestStatus<Hunt>;
  readonly isLoadingResultsByTypeCount: boolean;
}

const baseHuntPageState: HuntPageState = {
  huntId: undefined,
  patchHuntRequestStatus: undefined,
  isLoadingResultsByTypeCount: false,
};

function toHuntResultsTableTabConfig(
  pt: PayloadType,
  resultCount: string,
): HuntResultsTableTabConfig {
  return {
    tabName: PAYLOAD_TYPE_TRANSLATION[pt]?.tabName || pt,
    payloadType: pt,
    totalResultsCount: Number(resultCount),
  };
}

/**
 * Function that generates the Hunt Result Tab configuration list, to be
 * consumed by the HuntResults component.
 */
export function generateResultTabConfigList(
  hunt: Pick<Hunt, 'failedClientsCount' | 'crashedClientsCount'>,
  resultCountPerType: readonly ApiTypeCount[],
): HuntResultsTableTabConfig[] {
  const tabs: HuntResultsTableTabConfig[] = [];

  const clientErrorCount = hunt.failedClientsCount;

  // We add the 'Errors' tab if necessary:
  if (clientErrorCount > BigInt(0)) {
    const errorTabConfig = toHuntResultsTableTabConfig(
      PayloadType.API_HUNT_ERROR,
      `${clientErrorCount}`,
    );

    tabs.push(errorTabConfig);
  }

  if (resultCountPerType.length === 0) return tabs;

  const resultTabs = resultCountPerType
    .filter((item) => isNonNull(item?.type) && isNonNull(item.count))
    .map((item) =>
      toHuntResultsTableTabConfig(item.type! as PayloadType, item.count!),
    );

  tabs.push(...resultTabs);

  return tabs.sort((a, b) => (a.tabName < b.tabName ? -1 : 1));
}

/** Maximum number of progress data-points to fetch per Hunt */
const MAX_HUNT_COMPLETION_PROGRESS_DATAPOINTS = 100;

/** ComponentStore implementation used by the GlobalStore. */
class HuntPageComponentStore extends ComponentStore<HuntPageState> {
  constructor(private readonly httpApiService: HttpApiService) {
    super(baseHuntPageState);
  }

  /** Reducer resetting the store and setting the huntId. */
  readonly selectHunt = this.updater<string>((state, huntId) => {
    // Clear complete state when new hunt is selected to prevent stale
    // information.
    return {
      ...baseHuntPageState,
      huntId,
    };
  });

  /** An observable emitting the hunt id of the selected hunt. */
  readonly selectedHuntId$: Observable<string | null> = this.select(
    (state) => state.huntId ?? null,
  ).pipe(distinctUntilChanged(), shareReplay({bufferSize: 1, refCount: true}));

  private readonly filteredSelectedHuntId$ = this.selectedHuntId$.pipe(
    filter(isNonNull),
  );

  private readonly periodicallyPolledHunt$ = this.selectedHuntId$.pipe(
    switchMap((huntId) =>
      huntId
        ? this.httpApiService.subscribeToHunt(huntId).pipe(startWith(null))
        : of(null),
    ),
    map((hunt) => (hunt ? translateHunt(hunt) : null)),
    shareReplay({bufferSize: 1, refCount: true}),
  );

  private readonly periodicallyPolledHuntProgress$ =
    this.filteredSelectedHuntId$.pipe(
      switchMap((huntId) =>
        this.httpApiService.subscribeToHuntClientCompletionStats({
          huntId,
          size: `${MAX_HUNT_COMPLETION_PROGRESS_DATAPOINTS}`,
        }),
      ),
    );

  readonly huntProgress$ = this.periodicallyPolledHuntProgress$;
  readonly huntResultsByTypeCountLoading$ = this.select(
    (state) => state.isLoadingResultsByTypeCount,
  );

  readonly patchHuntRequestStatus$ = this.select(
    (state) => state.patchHuntRequestStatus,
  );

  private readonly patchedHunt$ = this.patchHuntRequestStatus$.pipe(
    map((req) => (req?.status === RequestStatusType.SUCCESS ? req.data : null)),
    filter(isNonNull),
  );

  /** An observable emitting the hunt loaded by `selectHunt`. */
  readonly selectedHunt$: Observable<Hunt | null> = merge(
    this.periodicallyPolledHunt$,
    this.patchedHunt$,
  );

  readonly huntResultTabs$: Observable<HuntResultsTableTabConfig[] | null> =
    this.selectedHunt$.pipe(
      filter((hunt) => isNonNull(hunt) && hunt.state !== HuntState.NOT_STARTED),
      tap(() => {
        this.patchState({isLoadingResultsByTypeCount: true});
      }),
      switchMap((hunt) => {
        return this.httpApiService
          .subscribeToHuntResultsCountByType(hunt!.huntId)
          .pipe(
            tap(() => {
              this.patchState({isLoadingResultsByTypeCount: false});
            }),
            map((res) => generateResultTabConfigList(hunt!, res?.items || [])),
          );
      }),
    );

  /**
   * An effect requesting to update the hunt state.
   */
  readonly patchHunt = this.effect<{
    state?: HuntState;
    clientLimit?: bigint;
    clientRate?: number;
  }>((obs$) =>
    obs$.pipe(
      withLatestFrom(this.state$),
      switchMap(([patch, storeState]) =>
        trackRequest(
          this.httpApiService
            .patchHunt(storeState.huntId ?? '', patch)
            .pipe(map((hunt) => translateHunt(hunt))),
        ),
      ),
      tap((patchHuntRequestStatus) => {
        this.patchState({patchHuntRequestStatus});
      }),
    ),
  );
}

/** GlobalStore for hunt page related API calls. */
@Injectable({
  providedIn: 'root',
})
export class HuntPageGlobalStore {
  constructor(private readonly httpApiService: HttpApiService) {
    this.store = new HuntPageComponentStore(this.httpApiService);
    this.selectedHuntId$ = this.store.selectedHuntId$;
    this.selectedHunt$ = this.store.selectedHunt$;
    this.huntProgress$ = this.store.huntProgress$;
    this.huntResultTabs$ = this.store.huntResultTabs$;
    this.huntResultsByTypeCountLoading$ =
      this.store.huntResultsByTypeCountLoading$;
  }

  private readonly store;

  /** Selects a hunt with a given id. */
  selectHunt(huntId: string): void {
    this.store.selectHunt(huntId);
  }

  readonly selectedHuntId$;
  readonly selectedHunt$;

  readonly huntProgress$;
  readonly huntResultTabs$;
  readonly huntResultsByTypeCountLoading$;

  cancelHunt() {
    this.store.patchHunt({state: HuntState.CANCELLED});
  }

  startHunt() {
    this.store.patchHunt({state: HuntState.RUNNING});
  }

  modifyAndStartHunt(params: {clientLimit: bigint; clientRate: number}) {
    this.store.patchHunt({...params, state: HuntState.RUNNING});
  }
}
