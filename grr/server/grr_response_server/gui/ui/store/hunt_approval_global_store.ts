import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {Observable, of} from 'rxjs';
import {distinctUntilChanged, filter, map, shareReplay, startWith, switchMap, takeWhile, tap} from 'rxjs/operators';

import {ApiHuntApproval} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {extractErrorMessage, RequestStatus, trackRequest} from '../lib/api/track_request';
import {translateHuntApproval} from '../lib/api_translation/hunt';
import {HuntApproval, HuntApprovalRequest} from '../lib/models/hunt';
import {isNonNull} from '../lib/preconditions';

import {UserGlobalStore} from './user_global_store';

interface HuntApprovalState {
  readonly huntId?: string;
  readonly requestApprovalStatus?: RequestStatus<HuntApproval, string>;
}

/** ComponentStore implementation used by the GlobalStore. */
class HuntApprovalComponentStore extends ComponentStore<HuntApprovalState> {
  constructor(
      private readonly httpApiService: HttpApiService,
  ) {
    super({});
  }

  /** Reducer resetting the store and setting the huntId. */
  readonly selectHunt = this.updater<string>((state, huntId) => {
    if (state.huntId === huntId) {
      return state;
    }

    // Clear complete state when new hunt is selected to prevent stale
    // information.
    return {
      huntId,
    };
  });

  /** An observable emitting the hunt id of the selected hunt. */
  readonly selectedHuntId$: Observable<string|null> =
      this.select(state => state.huntId ?? null)
          .pipe(
              distinctUntilChanged(),
          );

  private readonly approvals$ = this.selectedHuntId$.pipe(
      switchMap(huntId => {
        if (!huntId) {
          return of(null);
        }

        return this.httpApiService.subscribeToListHuntApprovals(huntId).pipe(
            map((approvals: readonly ApiHuntApproval[]): HuntApproval[] =>
                    approvals?.map(translateHuntApproval)),
            takeWhile(
                (approvals: HuntApproval[]) => !approvals?.find(
                    approval => approval.status.type === 'valid'),
                true),
        );
      }),
  );

  /** An observable emitting the latest non-expired approval. */
  readonly latestApproval$: Observable<HuntApproval|null> =
      this.approvals$.pipe(
          // Approvals are expected to be in reversed chronological order.
          map(approvals =>
                  approvals?.find(
                      (approval) => approval?.status.type !== 'expired') ??
                  null),
          shareReplay({bufferSize: 1, refCount: true}),
      );

  readonly huntApprovalRoute$: Observable<string[]> = this.latestApproval$.pipe(
      filter(isNonNull), map((latestApproval: HuntApproval): string[] => {
        return [
          'hunts',
          latestApproval.huntId,
          'users',
          latestApproval.requestor,
          'approvals',
          latestApproval.approvalId,
        ];
      }), startWith([]));

  readonly hasAccess$: Observable<boolean|null> = this.selectedHuntId$.pipe(
      switchMap(
          huntId => huntId ?
              this.httpApiService.subscribeToVerifyHuntAccess(huntId).pipe(
                  takeWhile(hasAccess => !hasAccess, true),
                  startWith(null),
                  ) :
              of(null)),
      shareReplay({bufferSize: 1, refCount: true}),
  );

  readonly requestApprovalStatus$:
      Observable<RequestStatus<HuntApproval, string>|null> =
          this.select(state => state.requestApprovalStatus ?? null);

  /** An effect requesting a new hunt approval. */
  readonly requestHuntApproval = this.effect<HuntApprovalRequest>(
      obs$ => obs$.pipe(
          switchMap(
              approvalRequest => trackRequest(
                  this.httpApiService.requestHuntApproval(approvalRequest)
                      .pipe(map(translateHuntApproval)))),
          map(extractErrorMessage),
          tap(requestApprovalStatus => {
            this.patchState({requestApprovalStatus});
          }),
          ));
}

/** GlobalStore for hunt approval related API calls. */
@Injectable({
  providedIn: 'root',
})
export class HuntApprovalGlobalStore {
  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly userGlobalStore: UserGlobalStore,
  ) {}

  private readonly store = new HuntApprovalComponentStore(this.httpApiService);

  /** An observable emitting latest non-expired approval. */
  readonly latestApproval$: Observable<HuntApproval|null> =
      this.store.latestApproval$;

  /** An observable emitting latest approval route. */
  readonly huntApprovalRoute$: Observable<string[]> =
      this.store.huntApprovalRoute$;

  /** An obserable emitting if the user has access to the hunt. */
  readonly hasAccess$ = this.store.hasAccess$;

  /**
   * An observable emitting if the hunt approval system is enabled for the user.
   */
  readonly huntApprovalRequired$ = this.userGlobalStore.currentUser$.pipe(
      map(user => user.huntApprovalRequired));

  readonly requestApprovalStatus$:
      Observable<RequestStatus<HuntApproval, string>|null> =
          this.store.requestApprovalStatus$;

  /** Selects a hunt with a given id. */
  selectHunt(huntId: string): void {
    this.store.selectHunt(huntId);
  }

  /** Requests an approval for the currently selected hunt. */
  requestHuntApproval(request: HuntApprovalRequest): void {
    this.store.requestHuntApproval(request);
    this.selectHunt(request.huntId);
  }
}
