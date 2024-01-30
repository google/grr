import {Injectable} from '@angular/core';
import {Observable, of} from 'rxjs';

import {ApiListHuntResultsArgs} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {getHuntResultKey} from '../lib/api_translation/hunt';
import {HuntResultOrError, PayloadType} from '../lib/models/result';
import {compareDateOldestFirst} from '../lib/type_utils';

import {ApiCollectionStore, PaginationArgs} from './store_util';

/** Store that fetches and keeps results for a specific Hunt. */
class HuntResultsStore<T extends HuntResultOrError> extends ApiCollectionStore<
  T,
  ApiListHuntResultsArgs
> {
  protected loadResults(
    args: ApiListHuntResultsArgs,
    paginationArgs: PaginationArgs,
  ): Observable<readonly T[]> {
    if (!args.huntId) return of([]);

    if (args.withType === PayloadType.API_HUNT_ERROR) {
      return this.httpApiService.listErrorsForHunt({
        huntId: args.huntId,
        offset: paginationArgs.offset?.toString(),
        count: paginationArgs.count?.toString(),
      }) as Observable<readonly T[]>;
    }

    return this.httpApiService.listResultsForHunt({
      huntId: args.huntId,
      withType: args.withType,
      offset: paginationArgs.offset?.toString(),
      count: paginationArgs.count?.toString(),
    }) as Observable<readonly T[]>;
  }

  readonly compareItems = compareDateOldestFirst<T>(
    (r) => new Date(r.timestamp!),
  );

  protected areItemsEqual(a: T, b: T): boolean {
    return getHuntResultKey(a, '') === getHuntResultKey(b, '');
  }

  protected override areArgsEqual(
    a: ApiListHuntResultsArgs,
    b: ApiListHuntResultsArgs,
  ): boolean {
    return a.huntId === b.huntId && a.withType === b.withType;
  }
}

/**
 * Service that acts as a "facade" to communicate with the Hunt Results Store.
 */
@Injectable()
export class HuntResultsLocalStore<T extends HuntResultOrError> {
  constructor(private readonly httpApiService: HttpApiService) {}

  private readonly store = new HuntResultsStore<T>(this.httpApiService);

  readonly results$: Observable<readonly T[]> = this.store.results$;
  readonly isLoading$ = this.store.isLoading$;

  loadMore(count?: number) {
    this.store.loadMore(count);
  }

  setArgs(args: ApiListHuntResultsArgs): void {
    this.store.setArgs(args);
  }
}
