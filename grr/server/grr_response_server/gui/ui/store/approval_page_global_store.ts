import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {merge, Observable, of} from 'rxjs';
import {filter, map, switchMap, tap, withLatestFrom} from 'rxjs/operators';

import {HttpApiService} from '../lib/api/http_api_service';
import {RequestStatus, RequestStatusType, trackRequest} from '../lib/api/track_request';
import {translateApproval} from '../lib/api_translation/client';
import {ClientApproval} from '../lib/models/client';
import {assertNonNull, isNonNull} from '../lib/preconditions';

interface ApprovalPageState {
  readonly selectedApprovalKey?: ApprovalKey;
  readonly grantRequestStatus?: RequestStatus<ClientApproval>;
}

interface ApprovalKey {
  readonly approvalId: string;
  readonly clientId: string;
  readonly requestor: string;
}


/** ComponentStore implementation used by the ApprovalPageGlobalStore. */
class ApprovalPageComponentStore extends ComponentStore<ApprovalPageState> {
  constructor(
      private readonly httpApiService: HttpApiService,
  ) {
    super({});
  }

  readonly grantRequestStatus$ = this.select(state => state.grantRequestStatus);

  readonly selectApproval = this.updater<ApprovalKey>(
      (state, selectedApprovalKey) => ({selectedApprovalKey}));

  private readonly grantedApproval$ = this.grantRequestStatus$.pipe(
      map(req => req?.status === RequestStatusType.SUCCESS ? req.data : null),
      filter(isNonNull),
  );

  readonly approval$: Observable<ClientApproval|null> = merge(
      this.grantedApproval$,
      this.select(state => state.selectedApprovalKey)
          .pipe(
              switchMap(
                  (key) => key ?
                      this.httpApiService.subscribeToClientApproval(key).pipe(
                          map(translateApproval)) :
                      of(null)),
              ),
  );

  readonly grantApproval = this.effect<void>(
      obs$ => obs$.pipe(
          withLatestFrom(this.select(state => state.selectedApprovalKey)),
          switchMap(([, key]) => {
            assertNonNull(key, 'approval key');
            return trackRequest(
                this.httpApiService.grantClientApproval(key).pipe(
                    map(translateApproval)),
            );
          }),
          tap((grantRequestStatus) => {
            this.patchState({grantRequestStatus});
          }),
          ));
}

/** Store that loads and stores data for the approval page. */
@Injectable({
  providedIn: 'root',
})
export class ApprovalPageGlobalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new ApprovalPageComponentStore(this.httpApiService);

  readonly approval$: Observable<ClientApproval|null> = this.store.approval$;

  readonly grantRequestStatus$ = this.store.grantRequestStatus$;

  selectApproval(approvalKey: ApprovalKey): void {
    this.store.selectApproval(approvalKey);
  }

  grantApproval(): void {
    this.store.grantApproval();
  }
}
