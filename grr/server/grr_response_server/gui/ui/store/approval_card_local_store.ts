import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {concatMap, tap} from 'rxjs/operators';

import {HttpApiService} from '../lib/api/http_api_service';
import {RequestStatusType, trackRequest} from '../lib/api/track_request';
import {translateApproverSuggestions} from '../lib/api_translation/user';

interface ApprovalCardState {
  readonly approverSuggestions?: readonly string[];
}

/** ComponentStore implementation used by the LocalStore. */
class ApprovalCardComponentStore extends ComponentStore<ApprovalCardState> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({});
  }

  private readonly updateApproverSuggestions = this.updater<readonly string[]>(
    (state, approverSuggestions) => {
      return {
        ...state,
        approverSuggestions,
      };
    },
  );

  readonly suggestApprovers = this.effect<string>((obs$) =>
    obs$.pipe(
      concatMap((usernameQuery) =>
        trackRequest(this.httpApiService.suggestApprovers(usernameQuery)),
      ),
      tap((status) => {
        if (status.status === RequestStatusType.SUCCESS) {
          this.updateApproverSuggestions(
            translateApproverSuggestions(status.data),
          );
        }
      }),
    ),
  );

  readonly approverSuggestions$ = this.select(
    (state) => state.approverSuggestions,
  );
}

/** Store for approval-related API calls. */
@Injectable()
export class ApprovalCardLocalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new ApprovalCardComponentStore(this.httpApiService);

  suggestApprovers(usernameQuery: string) {
    this.store.suggestApprovers(usernameQuery);
  }

  readonly approverSuggestions$ = this.store.approverSuggestions$;
}
