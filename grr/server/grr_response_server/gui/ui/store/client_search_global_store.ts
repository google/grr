import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {Observable} from 'rxjs';
import {filter, map, switchMap, tap, withLatestFrom} from 'rxjs/operators';

import {HttpApiService} from '../lib/api/http_api_service';
import {translateClient} from '../lib/api_translation/client';
import {Client} from '../lib/models/client';
import {isNonNull} from '../lib/preconditions';
import {compareDateNewestFirst} from '../lib/type_utils';

interface ClientSearchState {
  readonly clients?: ReadonlyArray<Client>;
  readonly query?: string;
}

const NULL_DATE = new Date(0);

/**
 * Store used by the ClientSearchGlobalStore.
 */
class ClientSearchStore extends ComponentStore<ClientSearchState> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({});

    // Upon search query change, load new search results from the backend.
    this.query$.subscribe(() => {
      this.executeSearchClientQuery();
    });
  }

  /** Updates the query, resetting search results when query changes. */
  readonly searchClients =
      this.updater<string>((state, query) => ({
                             ...state,
                             query,
                             clients: query === state.query ? state.clients : undefined,
                           }));

  readonly clients$ = this.select((state) => state.clients);

  private readonly query$ = this.select(state => state.query);

  private readonly updateClients = this.updater<ReadonlyArray<Client>>(
      (state, clients) => ({
        ...state,
        clients: [...clients].sort(
            compareDateNewestFirst(c => c.lastSeenAt ?? NULL_DATE)),
      }));

  private readonly executeSearchClientQuery = this.effect<void>(
      trigger$ => trigger$.pipe(
          withLatestFrom(this.query$),
          map(([, query]) => query),
          filter(isNonNull),
          filter(query => query !== ''),
          switchMap(
              (query) => this.httpApiService.searchClients(
                  {query, offset: 0, count: 100})),
          map(apiResult => apiResult.items?.map(translateClient) ?? []),
          tap(results => {
            this.updateClients(results);
          }),
          ));
}

/**
 * GlobalStore for the client search.
 */
@Injectable({
  providedIn: 'root',
})
export class ClientSearchGlobalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new ClientSearchStore(this.httpApiService);

  /**
   * An observable emitting the list of fetched Clients on every search. The
   * empty list indicates 0 search results. undefined indicates that results are
   * being queried.
   */
  readonly clients$: Observable<ReadonlyArray<Client>|undefined> =
      this.store.clients$;

  /**
   * Searches for clients using the current search query.
   */
  searchClients(query: string): void {
    this.store.searchClients(query);
  }
}
