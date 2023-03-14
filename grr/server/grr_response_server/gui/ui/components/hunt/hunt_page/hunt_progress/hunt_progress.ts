import {Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {HuntPageGlobalStore} from '../../../../store/hunt_page_global_store';
import {ColorScheme} from '../../../flow_details/helpers/result_accordion';

/** Summary describes information in a summary card. */
interface Summary {
  title: string;
  tooltip: string;
  relative: bigint;
  raw: bigint;
}

const BIG_ZERO = BigInt(0);

function getPercentage(part: bigint, all: bigint): bigint {
  if (part === BIG_ZERO || all === BIG_ZERO) return BIG_ZERO;

  return getPositiveOrZero(part * BigInt(100) / all);
}

function getPositiveOrZero(num: bigint): bigint {
  return num < BIG_ZERO ? BIG_ZERO : num;
}

/** Provides progress information for the current hunt. */
@Component({
  selector: 'app-hunt-progress',
  templateUrl: './hunt_progress.ng.html',
  styleUrls: ['./hunt_progress.scss'],
})
export class HuntProgress {
  protected readonly ColorScheme = ColorScheme;
  constructor(private readonly huntPageGlobalStore: HuntPageGlobalStore) {}

  protected readonly hunt$ = this.huntPageGlobalStore.selectedHunt$;

  protected overviewSummaries$: Observable<readonly Summary[]> =
      this.hunt$.pipe(map(hunt => {
        if (!hunt) return [];

        return [
          {
            title: 'Complete',
            tooltip: 'Clients that have finished the collection.',
            relative:
                getPercentage(hunt.completedClientsCount, hunt.allClientsCount),
            raw: getPositiveOrZero(hunt.completedClientsCount),
          },
          {
            title: 'In progress',
            tooltip: 'Scheduled clients (collection running).',
            relative:
                getPercentage(hunt.remainingClientsCount, hunt.allClientsCount),
            raw: getPositiveOrZero(hunt.remainingClientsCount),
          },
          {
            title: 'Without results',
            tooltip: 'Clients that finished with no result.',
            relative: getPercentage(
                hunt.completedClientsCount - hunt.clientsWithResultsCount,
                hunt.allClientsCount),
            raw: getPositiveOrZero(
                hunt.completedClientsCount - hunt.clientsWithResultsCount),
          },
          {
            title: 'With results',
            tooltip: 'Clients that finished with result',
            relative: getPercentage(
                hunt.clientsWithResultsCount, hunt.allClientsCount),
            raw: getPositiveOrZero(hunt.clientsWithResultsCount),
          },
        ];
      }));

  protected errorSummaries$: Observable<readonly Summary[]> =
      this.hunt$.pipe(map(hunt => {
        if (!hunt) return [];

        return [
          {
            title: 'Errors and Crashes',
            tooltip: 'Clients that had problems in the collection.',
            relative: getPercentage(
                hunt.crashedClientsCount + hunt.failedClientsCount,
                hunt.allClientsCount),
            raw: getPositiveOrZero(
                hunt.crashedClientsCount + hunt.failedClientsCount),
          },
        ];
      }));
}
