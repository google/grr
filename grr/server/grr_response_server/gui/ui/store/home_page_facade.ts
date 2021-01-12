import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateApproval} from '@app/lib/api_translation/client';
import {Observable, of} from 'rxjs';
import {filter, map, shareReplay, switchMap, tap} from 'rxjs/operators';

import {ClientApproval} from '../lib/models/client';
import {isNonNull} from '../lib/preconditions';

interface HomePageState {
  readonly recentClientApprovals?: ReadonlyArray<ClientApproval>;
}

/**
 * ComponentStore implementation used by the HomePageFacade. Shouldn't be
 * used directly. Declared as an exported global symbol to make dependency
 * injection possible.
 */
@Injectable({
  providedIn: 'root',
})
export class HomePageStore extends ComponentStore<HomePageState> {
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
export class HomePageFacade {
  constructor(private readonly store: HomePageStore) {}

  readonly recentClientApprovals$: Observable<ReadonlyArray<ClientApproval>> =
      this.store.recentClientApprovals$;
}
