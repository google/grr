import {CommonModule} from '@angular/common';
import {Component} from '@angular/core';
import {MatTooltipModule} from '@angular/material/tooltip';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {HuntPageGlobalStore} from '../../../../store/hunt_page_global_store';

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

  return part * BigInt(100) / all;
}

/** Provides progress information for the current hunt. */
@Component({
  selector: 'app-hunt-progress',
  templateUrl: './hunt_progress.ng.html',
  styleUrls: ['./hunt_progress.scss'],
  imports: [
    CommonModule,
    MatTooltipModule,
  ],
  standalone: true,
})
export class HuntProgress {
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
            raw: hunt.completedClientsCount,
          },
          {
            title: 'In progress',
            tooltip: 'Scheduled clients (collection running).',
            relative:
                getPercentage(hunt.remainingClientsCount, hunt.allClientsCount),
            raw: hunt.remainingClientsCount,
          },
          {
            title: 'Without results',
            tooltip: 'Clients that finished with no result.',
            relative: getPercentage(
                hunt.completedClientsCount - hunt.clientsWithResultsCount,
                hunt.allClientsCount),
            raw: hunt.completedClientsCount - hunt.clientsWithResultsCount,
          },
          {
            title: 'With results',
            tooltip: 'Clients that finished with result',
            relative: getPercentage(
                hunt.clientsWithResultsCount, hunt.allClientsCount),
            raw: hunt.clientsWithResultsCount,
          },
        ];
      }));
}
