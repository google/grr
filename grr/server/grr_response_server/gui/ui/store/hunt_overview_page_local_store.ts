import {Injectable} from '@angular/core';
import {ComponentStore} from '@ngrx/component-store';
import {Observable} from 'rxjs';
import {map, shareReplay, switchMap} from 'rxjs/operators';

import {ApiHunt, ApiListHuntsArgs} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';

// Dependency injection in constructor seems to not work without @Injectable()
// annotation.
@Injectable()
abstract class ApiStore<Result, Args extends {} = {}> {
  constructor(protected readonly httpApiService: HttpApiService) {}

  protected readonly store = new ComponentStore<Args>();

  setArgs(args: Args) {
    this.store.setState(args);
  }

  patchArgs(args: Partial<Args>) {
    this.store.patchState(args);
  }

  abstract loadResults(args: Args): Observable<Result>;

  results$: Observable<Result> = this.store.state$.pipe(
      switchMap(args => this.loadResults(args)),
      shareReplay({bufferSize: 1, refCount: true}),
  );
}

/** Store for HuntOverviewPage. */
@Injectable()
export class HuntOverviewPageLocalStore extends
    ApiStore<ReadonlyArray<ApiHunt>, ApiListHuntsArgs> {
  loadResults(args: ApiListHuntsArgs) {
    return this.httpApiService.subscribeToListHunts(args).pipe(
        map(response => response.items ?? []));
  }
}
