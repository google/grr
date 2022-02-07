import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {Observable, of} from 'rxjs';
import {filter, map, shareReplay, switchMap, tap} from 'rxjs/operators';

import {HttpApiService} from '../lib/api/http_api_service';
import {translateApproval} from '../lib/api_translation/client';
import {ClientApproval} from '../lib/models/client';
import {isNonNull} from '../lib/preconditions';

interface HomePageState {
  readonly recentClientApprovals?: ReadonlyArray<ClientApproval>;
}

/** ComponentStore implementation used by the HomePageGlobalStore. */
class HomePageComponentStore extends ComponentStore<HomePageState> {
  constructor(
      private readonly httpApiService: HttpApiService,
  ) {
    super({});
  }

  readonly recentClientApprovals$ = of(undefined).pipe(
      // Ensure that the query is done on subscription.
      tap(() => {
        this.fetchRecentClientApprovals();
      }),
      switchMap(() => this.select(state => state.recentClientApprovals)),
      filter(isNonNull),
      shareReplay(1),  // Ensure that the query is done just once.
  );

  private readonly fetchRecentClientApprovals = this.effect<void>(
      obs$ => obs$.pipe(
          switchMap(
              () => this.httpApiService.listRecentClientApprovals({count: 20})),
          map(approvals => approvals.map(translateApproval)),
          tap(approvals => {
            this.updateRecentApprovals(approvals);
          }),
          ));


  private readonly updateRecentApprovals =
      this.updater<ReadonlyArray<ClientApproval>>(
          (state, recentClientApprovals) => {
            return {...state, recentClientApprovals};
          });
}

/** Store that loads and stores data for the home page. */
@Injectable({
  providedIn: 'root',
})
export class HomePageGlobalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new HomePageComponentStore(this.httpApiService);

  readonly recentClientApprovals$: Observable<ReadonlyArray<ClientApproval>> =
      this.store.recentClientApprovals$;
}
