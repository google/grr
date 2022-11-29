import {Injectable} from '@angular/core';
import {Observable, of} from 'rxjs';
import {map} from 'rxjs/operators';

import {ApiSearchClientsArgs} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {translateClient} from '../lib/api_translation/client';
import {Client} from '../lib/models/client';
import {compareDateNewestFirst} from '../lib/type_utils';

import {ApiCollectionStore, PaginationArgs} from './store_util';

const NULL_DATE = new Date(0);

/**
 * Store used by the ClientSearchLocalStore.
 */
class ClientSearchStore extends
    ApiCollectionStore<Client, ApiSearchClientsArgs> {
  protected loadResults(
      args: ApiSearchClientsArgs,
      paginationArgs: PaginationArgs): Observable<readonly Client[]> {
    if (args.query?.trim() === '') {
      return of([]);
    }

    return this.httpApiService
        .searchClients({
          ...args,
          offset: paginationArgs.offset?.toString(),
          count: paginationArgs.count?.toString(),
        })
        .pipe(
            map(results => results.items?.map(translateClient) ?? []),
        );
  }

  readonly compareItems =
      compareDateNewestFirst<Client>(c => c.lastSeenAt ?? NULL_DATE);

  protected areItemsEqual(a: Client, b: Client): boolean {
    return a.clientId === b.clientId;
  }

  protected override areArgsEqual(
      a: ApiSearchClientsArgs, b: ApiSearchClientsArgs): boolean {
    return a.query === b.query;
  }
}

/**
 * GlobalStore for the client search.
 */
@Injectable({providedIn: 'any'})
export class ClientSearchLocalStore {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new ClientSearchStore(this.httpApiService);

  readonly clients$: Observable<ReadonlyArray<Client>|undefined> =
      this.store.results$;

  readonly isLoading$ = this.store.isLoading$;

  readonly hasMore$ = this.store.hasMore$;

  loadMore(count?: number) {
    this.store.loadMore(count);
  }

  searchClients(query: string): void {
    this.store.setArgs({query});
  }
}
