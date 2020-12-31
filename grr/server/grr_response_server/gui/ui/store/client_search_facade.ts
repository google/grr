import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {ApiSearchClientResult} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {translateClient} from '@app/lib/api_translation/client';
import {Client} from '@app/lib/models/client';
import {Observable, of} from 'rxjs';
import {map, switchMap, tap} from 'rxjs/operators';

interface ClientSearchState {
  readonly clients: {readonly [key: string]: Client};
  readonly clientSequence: ReadonlyArray<string>;
  readonly query: string;
}

/**
 * Store used by the ClientSearchFacade.
 */
@Injectable({
  providedIn: 'root',
})
export class ClientSearchStore extends ComponentStore<ClientSearchState> {
  constructor(private readonly httpApiService: HttpApiService) {
    super({
      clients: {},
      clientSequence: [],

      query: '',
    });
  }

  private readonly updateClients =
      this.updater<ReadonlyArray<Client>>((state, clients) => {
        const newClientsMap = {...state.clients};
        for (const c of clients) {
          newClientsMap[c.clientId] = c;
        }

        const newClientSequence = Object.values(newClientsMap);
        newClientSequence.sort((a, b) => {
          const bs = b.lastSeenAt || new Date(0);
          const as = a.lastSeenAt || new Date(0);
          return bs.getTime() - as.getTime();
        });

        return {
          ...state,
          clients: newClientsMap,
          clientSequence: newClientSequence.map(c => c.clientId),
        };
      });

  /**
   * An observable emitting the list of fetched Clients on every search.
   */
  readonly clients$: Observable<ReadonlyArray<Client>> =
      this.select((state) => {
        return state.clientSequence.map(id => state.clients[id]);
      });

  /**
   * An observable emitting the current query string every time it gets updated.
   */
  readonly query$: Observable<string> = this.select((state) => {
    return state.query;
  });

  /**
   * Searches for clients using the current search query.
   */
  readonly searchClients = this.effect<string>(
      obs$ => obs$.pipe(
          switchMap(query => {
            if (query) {
              return this.httpApiService.searchClients(
                  {query, offset: 0, count: 100});
            } else {
              return of<ApiSearchClientResult>({items: []});
            }
          }),
          map(apiResult => apiResult.items?.map(translateClient) ?? []),
          tap(results => {
            this.updateClients(results);
          })));
}

/**
 * Facade for the client search.
 */
@Injectable({
  providedIn: 'root',
})
export class ClientSearchFacade {
  constructor(private readonly store: ClientSearchStore) {}

  /**
   * An observable emitting the list of fetched Clients on every search.
   */
  readonly clients$: Observable<ReadonlyArray<Client>> = this.store.clients$;

  /**
   * An observable emitting the current query string every time it gets updated.
   */
  readonly query$: Observable<string> = this.store.query$;

  /**
   * Searches for clients using the current search query.
   */
  searchClients(query: string): void {
    this.store.searchClients(query);
  }
}
