import {DestroyRef, inject} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {
  patchState,
  signalStore,
  withMethods,
  withProps,
  withState,
} from '@ngrx/signals';

import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {ClientApproval} from '../lib/models/client';
import {HuntApproval} from '../lib/models/hunt';

interface ApprovalRequestStoreState {
  readonly requestedClientApproval: ClientApproval | null;
  readonly requestedFleetCollectionApproval: HuntApproval | null;
}

const initialState: ApprovalRequestStoreState = {
  requestedClientApproval: null,
  requestedFleetCollectionApproval: null,
};

/**
 * Store for storing an approval request from another users.
 * An approval request is only accessible when the user "knows" the
 * URL which contains the client id, approval id and requestor name.
 * As the information is passed via the url, we only need to store a
 * single approval.
 */
// tslint:disable-next-line:enforce-name-casing
export const ApprovalRequestStore = signalStore(
  {providedIn: 'root'},
  withState<ApprovalRequestStoreState>(initialState),
  withProps(() => ({
    httpApiService: inject(HttpApiWithTranslationService),
    destroyRef: inject(DestroyRef),
  })),
  withMethods(({httpApiService, destroyRef, ...store}) => ({
    fetchClientApproval(
      approvalId: string,
      clientId: string,
      requestor: string,
    ) {
      return httpApiService
        .fetchClientApproval({clientId, requestor, approvalId})
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((requestedClientApproval) => {
          patchState(store, {requestedClientApproval});
        });
    },

    grantClientApproval(approval: ClientApproval) {
      httpApiService
        .grantClientApproval({
          clientId: approval.clientId,
          requestor: approval.requestor,
          approvalId: approval.approvalId,
        })
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((requestedClientApproval) => {
          patchState(store, {requestedClientApproval});
        });
    },
    fetchFleetCollectionApproval(
      approvalId: string,
      fleetCollectionId: string,
      requestor: string,
    ) {
      return httpApiService
        .fetchHuntApproval({
          huntId: fleetCollectionId,
          requestor,
          approvalId,
        })
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((requestedFleetCollectionApproval) => {
          patchState(store, {requestedFleetCollectionApproval});
        });
    },

    grantFleetCollectionApproval(approval: HuntApproval) {
      httpApiService
        .grantHuntApproval({
          huntId: approval.huntId,
          requestor: approval.requestor,
          approvalId: approval.approvalId,
        })
        .pipe(takeUntilDestroyed(destroyRef))
        .subscribe((requestedFleetCollectionApproval) => {
          patchState(store, {requestedFleetCollectionApproval});
        });
    },
  })),
);
