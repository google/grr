import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {ApiListHuntsArgs} from '../lib/api/api_interfaces';
import {translateHunt} from '../lib/api_translation/hunt';
import {Hunt} from '../lib/models/hunt';
import {compareDateNewestFirst} from '../lib/type_utils';

import {ApiCollectionStore, PaginationArgs} from './store_util';

/** Store for HuntOverviewPage. */
@Injectable()
export class HuntOverviewPageLocalStore extends
    ApiCollectionStore<Hunt, ApiListHuntsArgs> {
  override readonly INITIAL_LOAD_COUNT = 5;

  protected loadResults(args: ApiListHuntsArgs, paginationArgs: PaginationArgs):
      Observable<readonly Hunt[]> {
    return this.httpApiService
        .subscribeToListHunts({
          ...args,
          count: paginationArgs.count.toString(),
          offset: paginationArgs.offset.toString(),
        })
        .pipe(
            map(response => (response.items ?? []).map(translateHunt)),
        );
  }

  protected readonly compareItems =
      compareDateNewestFirst<Hunt>(hunt => hunt.created);

  protected areItemsEqual(a: Hunt, b: Hunt): boolean {
    return a.huntId === b.huntId;
  }
}
