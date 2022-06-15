import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {MatTableDataSource} from '@angular/material/table';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {PAYLOAD_TYPE_TRANSLATION} from '../../../../lib/api_translation/result';
import {CellComponent, ColumnDescriptor} from '../../../../lib/models/result';
import {observeOnDestroy} from '../../../../lib/reactive';
import {HuntPageLocalStore} from '../../../../store/hunt_page_local_store';

/** Describes for a particular PayloadType, its render information. */
declare interface ResultsDescriptor {
  tabName?: string;
  columns: {[key: string]: ColumnDescriptor};
  displayedColumns?: string[];
  dataSource: MatTableDataSource<{[key: string]: unknown}>;
}

/**
 * Provides the forms for new hunt configuration.
 */
@Component({
  selector: 'app-hunt-results',
  templateUrl: './hunt_results.ng.html',
  styleUrls: ['./hunt_results.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntResults implements OnDestroy {
  readonly CellComponent = CellComponent;

  readonly ngOnDestroy = observeOnDestroy(this);

  // Maps payloadType to dataSource and columns.
  readonly resultsMap$: Observable<{[key: string]: ResultsDescriptor}> =
      this.huntPageLocalStore.huntResults$.pipe(map(state => {
        // TODO: persist `res` and dataSources in HuntResults,
        // refreshing only the `data` attribute on subscription.
        const res: {[key: string]: ResultsDescriptor} = {};
        if (!state || !state.results) return res;

        for (const result of state.results) {
          const pt = result.payloadType ?? '';

          // Start with default values for all ApiHuntResults.
          if (!res[pt]) {
            res[pt] = {
              columns: PAYLOAD_TYPE_TRANSLATION['ApiHuntResult'].columns,
              dataSource: new MatTableDataSource(),
              tabName: pt,
            };
          }
          const translateFn =
              PAYLOAD_TYPE_TRANSLATION['ApiHuntResult'].translateFn;
          const row: {[key: string]: unknown} = translateFn(result);

          // Now add complementary information if we have it (based on type).
          if (pt in PAYLOAD_TYPE_TRANSLATION) {
            const k = pt as keyof typeof PAYLOAD_TYPE_TRANSLATION;
            const cols = PAYLOAD_TYPE_TRANSLATION[k].columns;

            res[pt].columns = Object.assign(res[pt].columns, cols);
            res[pt].tabName = PAYLOAD_TYPE_TRANSLATION[k]?.tabName;

            const translateFunc = PAYLOAD_TYPE_TRANSLATION[k].translateFn;
            const trans = translateFunc(result.payload);
            for (const [key, value] of Object.entries(trans)) {
              row[key] = value;
            }
          }

          res[pt].dataSource.data.push(row);
          res[pt].displayedColumns = Object.keys(res[pt].columns);
        }

        return res;
      }));

  constructor(
      private readonly huntPageLocalStore: HuntPageLocalStore,
  ) {
    // TODO: Provide a way to loadMoreResults() outside the
    // constructor.
    huntPageLocalStore.loadMoreResults();
  }

  trackByIndex(index: number) {
    return index;
  }
}
