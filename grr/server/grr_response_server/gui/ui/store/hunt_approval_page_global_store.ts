import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {merge, Observable, of} from 'rxjs';
import {filter, map, switchMap, tap, withLatestFrom} from 'rxjs/operators';

import {HttpApiService} from '../lib/api/http_api_service';
import {RequestStatus, RequestStatusType, trackRequest} from '../lib/api/track_request';
import {translateHuntApproval} from '../lib/api_translation/hunt';
import {HuntApproval, HuntApprovalKey} from '../lib/models/hunt';
import {assertNonNull, isNonNull} from '../lib/preconditions';


interface HuntApprovalPageState {
  readonly selectedHuntApprovalKey?: HuntApprovalKey;
  readonly grantRequestStatus?: RequestStatus<HuntApproval>;
}


/** ComponentStore implementation used by the HuntApprovalPageGlobalStore. */
class HuntApprovalPageComponentStore extends
    ComponentStore<HuntApprovalPageState> {
  constructor(
      private readonly httpApiService: HttpApiService,
  ) {
    super({});
  }

  readonly selectHuntApproval = this.updater<HuntApprovalKey>(
      (state, selectedHuntApprovalKey) => ({selectedHuntApprovalKey}));

  readonly grantRequestStatus$ = this.select(state => state.grantRequestStatus);

  private readonly grantedApproval$ = this.grantRequestStatus$.pipe(
      map(req => req?.status === RequestStatusType.SUCCESS ? req.data : null),
      filter(isNonNull),
  );


  readonly approval$: Observable<HuntApproval|null> = merge(
      this.grantedApproval$,
      this.select(state => state.selectedHuntApprovalKey)
          .pipe(
              switchMap(
                  (key) => key ?
                      this.httpApiService.subscribeToHuntApproval(key).pipe(
                          map(translateHuntApproval)) :
                      of(null)),
              ),
  );

  readonly grantApproval = this.effect<void>(
      obs$ => obs$.pipe(
          withLatestFrom(this.select(state => state.selectedHuntApprovalKey)),
          switchMap(([, key]) => {
            assertNonNull(key, 'approval key');
            return trackRequest(
                this.httpApiService.grantHuntApproval(key).pipe(
                    map(translateHuntApproval)),
            );
          }),
          tap((grantRequestStatus) => {
            this.patchState({grantRequestStatus});
          }),
          ));
}

/** Store that loads and stores data for the HuntApproval page. */
@Injectable({
  providedIn: 'root',
})
export class HuntApprovalPageGlobalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store =
      new HuntApprovalPageComponentStore(this.httpApiService);

  readonly approval$: Observable<HuntApproval|null> = this.store.approval$;

  readonly grantRequestStatus$ = this.store.grantRequestStatus$;

  selectHuntApproval(huntApprovalKey: HuntApprovalKey): void {
    this.store.selectHuntApproval(huntApprovalKey);
  }

  grantApproval(): void {
    this.store.grantApproval();
  }
}
