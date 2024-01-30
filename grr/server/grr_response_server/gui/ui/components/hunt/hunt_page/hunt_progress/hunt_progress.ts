import {Component} from '@angular/core';
import {combineLatest, Observable} from 'rxjs';
import {filter, map, startWith, take} from 'rxjs/operators';

import {
  ApiGetHuntClientCompletionStatsResult,
  SampleFloat,
} from '../../../../lib/api/api_interfaces';
import {LineChartDatapoint} from '../../../../lib/dataviz/line_chart';
import {HuntCompletionProgressTableRow} from '../../../../lib/models/hunt';
import {isNonNull, isNull} from '../../../../lib/preconditions';
import {HuntPageGlobalStore} from '../../../../store/hunt_page_global_store';
import {ColorScheme} from '../../../flow_details/helpers/result_accordion';
import {HuntProgressLineChartDataset} from '../hunt_progress_chart/hunt_progress_chart';

/** Summary describes information in a summary card. */
interface Summary {
  title: string;
  tooltip: string;
  relative: bigint;
  raw: bigint;
}

const FIVE_MINUTES_IN_SECONDS = 5 * 60;
const BIG_ZERO = BigInt(0);

enum HuntProgressTabIndex {
  CHART_TAB = 0,
  TABLE_TAB = 1,
}

function getPercentage(part: bigint, all: bigint): bigint {
  if (part === BIG_ZERO || all === BIG_ZERO) return BIG_ZERO;

  return getPositiveOrZero((part * BigInt(100)) / all);
}

function getPositiveOrZero(num: bigint): bigint {
  return num < BIG_ZERO ? BIG_ZERO : num;
}

/**
 * Groups Hunt-progress data-points in "buckets" to make information in
 * the Hunt-progress table more digestible.
 */
function bucketizeHuntProgressData(
  startTimestamp: number,
  bucketSize: number,
  totalClientsCount: bigint | undefined,
  scheduledClientsDataPoints: readonly SampleFloat[],
  completedClientsDataPoints: readonly SampleFloat[],
): HuntCompletionProgressTableRow[] {
  const buckets = new Map<number, HuntCompletionProgressTableRow>();

  addClientSetToBuckets(
    buckets,
    startTimestamp,
    bucketSize,
    totalClientsCount,
    scheduledClientsDataPoints,
    'scheduledClients',
    'scheduledClientsPct',
  );

  addClientSetToBuckets(
    buckets,
    startTimestamp,
    bucketSize,
    totalClientsCount,
    completedClientsDataPoints,
    'completedClients',
    'completedClientsPct',
  );

  return Array.from(buckets.values()).sort((a, b) => a.timestamp - b.timestamp);
}

/** Updates @param buckets with grouped hunt progress data-points. */
function addClientSetToBuckets(
  buckets: Map<number, HuntCompletionProgressTableRow>,
  startTimestamp: number,
  bucketSize: number,
  totalClientsCount: bigint | undefined,
  huntProgressDataPoints: readonly SampleFloat[],
  rawValueKey: 'scheduledClients' | 'completedClients',
  pctValueKey: 'scheduledClientsPct' | 'completedClientsPct',
): void {
  let currentBucketTimestamp = startTimestamp + bucketSize;

  huntProgressDataPoints.forEach((dataPoint) => {
    const currentItemTimestamp = dataPoint.xValue;
    const clientsCount = dataPoint.yValue;

    if (typeof currentItemTimestamp !== 'number') return;

    while (currentItemTimestamp > currentBucketTimestamp) {
      currentBucketTimestamp = currentBucketTimestamp + bucketSize;
    }

    if (typeof clientsCount !== 'number') return;

    const bigClientsCount = BigInt(clientsCount);
    const bigClientsCountPct =
      totalClientsCount && getPercentage(bigClientsCount, totalClientsCount);

    const bucket: HuntCompletionProgressTableRow = {
      // Convert floating-point seconds to milliseconds:
      timestamp: currentBucketTimestamp * 1_000,
      [rawValueKey]: bigClientsCount,
      [pctValueKey]: bigClientsCountPct,
    };

    buckets.set(currentBucketTimestamp, {
      // We update the actual bucket (if present), as the latest value within
      // a bucket (timestamp range) already contains the accumulated data:
      ...buckets.get(currentBucketTimestamp),
      ...bucket,
    });
  });
}

/**
 * Removes entries/datapoints with a duplicated X axis value, keeping the one
 * with the highest Y-Axis value (the datapoint with the most information about
 * client completion progress).
 */
function prepareHuntProgressChartTimeSeriesData(
  series: readonly LineChartDatapoint[],
): LineChartDatapoint[] {
  // We first sort the dataset backwards, based on the X Axis value:
  const backwardsSortedSeries = [...series]
    .sort((a, b) => b.y - a.y)
    .sort((a, b) => b.x - a.x);

  const existingValues = new Set<number>();

  const backwardsSortedFilteredSeries = backwardsSortedSeries.filter((dp) => {
    if (existingValues.has(dp.x)) return false;

    existingValues.add(dp.x);

    return true;
  });

  return backwardsSortedFilteredSeries.reverse();
}

function toHuntCompletionChartData(
  progressData: ApiGetHuntClientCompletionStatsResult,
): HuntProgressLineChartDataset {
  const completedClients = prepareHuntProgressChartTimeSeriesData(
    toSafeLineChartData(progressData?.completePoints),
  );
  const inProgressClients = prepareHuntProgressChartTimeSeriesData(
    toSafeLineChartData(progressData?.startPoints),
  );

  const huntProgressLineChartDataset: HuntProgressLineChartDataset = {
    completedClients,
    inProgressClients,
  };

  return huntProgressLineChartDataset;
}

function toSafeLineChartData(
  dataset?: readonly SampleFloat[],
): LineChartDatapoint[] {
  if (isNull(dataset)) return [];

  return dataset
    .filter(
      (
        dataPoint, // We discard incomplete dataPoints:
      ) => isNonNull(dataPoint.xValue) && isNonNull(dataPoint.yValue),
    )
    .map((dataPoint) => ({
      // Convert floating-point seconds to milliseconds:
      x: dataPoint.xValue! * 1_000,
      y: dataPoint.yValue!,
    }));
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
  protected readonly huntProgress$ = this.huntPageGlobalStore.huntProgress$;
  protected readonly showHuntProgress$ = this.huntProgress$.pipe(
    map((progress) => {
      const startPoints = progress?.startPoints?.length ?? 0;
      const completePoints = progress?.completePoints?.length ?? 0;

      return startPoints > 0 || completePoints > 0;
    }),
  );

  protected readonly huntProgressLoading$ = this.huntProgress$.pipe(
    map((huntProgress) => isNull(huntProgress)),
    startWith(true),
  );

  protected overviewSummaries$: Observable<readonly Summary[]> =
    this.hunt$.pipe(
      map((hunt) => {
        if (!hunt) return [];

        return [
          {
            title: 'Complete',
            tooltip: 'Clients that have finished the collection.',
            relative: getPercentage(
              hunt.completedClientsCount,
              hunt.allClientsCount,
            ),
            raw: getPositiveOrZero(hunt.completedClientsCount),
          },
          {
            title: 'In progress',
            tooltip: 'Scheduled clients (collection running).',
            relative: getPercentage(
              hunt.remainingClientsCount,
              hunt.allClientsCount,
            ),
            raw: getPositiveOrZero(hunt.remainingClientsCount),
          },
          {
            title: 'Without results',
            tooltip: 'Clients that finished with no result.',
            relative: getPercentage(
              hunt.completedClientsCount - hunt.clientsWithResultsCount,
              hunt.allClientsCount,
            ),
            raw: getPositiveOrZero(
              hunt.completedClientsCount - hunt.clientsWithResultsCount,
            ),
          },
          {
            title: 'With results',
            tooltip: 'Clients that finished with result',
            relative: getPercentage(
              hunt.clientsWithResultsCount,
              hunt.allClientsCount,
            ),
            raw: getPositiveOrZero(hunt.clientsWithResultsCount),
          },
        ];
      }),
    );

  protected errorSummaries$: Observable<readonly Summary[]> = this.hunt$.pipe(
    map((hunt) => {
      if (!hunt) return [];

      return [
        {
          title: 'Errors and Crashes',
          tooltip: 'Clients that had problems in the collection.',
          relative: getPercentage(
            hunt.crashedClientsCount + hunt.failedClientsCount,
            hunt.allClientsCount,
          ),
          raw: getPositiveOrZero(
            hunt.crashedClientsCount + hunt.failedClientsCount,
          ),
        },
      ];
    }),
  );

  readonly huntProgressTableData$: Observable<
    HuntCompletionProgressTableRow[]
  > = combineLatest([this.huntProgress$, this.hunt$]).pipe(
    filter(([tableData, hunt]) => isNonNull(hunt) && isNonNull(tableData)),
    map(([tableData, hunt]) =>
      this.toHuntCompletionTableData(tableData, hunt?.allClientsCount),
    ),
  );
  readonly huntProgressChartData$: Observable<HuntProgressLineChartDataset> =
    this.huntProgress$.pipe(
      filter((progressData) => isNonNull(progressData)),
      map((progressData) => toHuntCompletionChartData(progressData)),
    );
  readonly huntProgressInitiallySelectedTab$ = this.huntProgressChartData$.pipe(
    map((chartData) => {
      // We need at least 2 datapoints in a series in order to render a line:
      const hasEnoughChartData =
        chartData.completedClients.length >= 2 ||
        chartData.inProgressClients.length >= 2;

      return hasEnoughChartData
        ? HuntProgressTabIndex.CHART_TAB
        : HuntProgressTabIndex.TABLE_TAB;
    }),
    // We are only interested in the first emission:
    take(1),
  );

  private toHuntCompletionTableData(
    huntCompletionStatusdata: ApiGetHuntClientCompletionStatsResult,
    totalClients: bigint | undefined,
  ): HuntCompletionProgressTableRow[] {
    const scheduledPoints = huntCompletionStatusdata.startPoints || [];
    const completedPoints = huntCompletionStatusdata.completePoints || [];

    if (scheduledPoints.length === 0 && completedPoints.length === 0) return [];

    const startTimestamp = Math.min(
      scheduledPoints[0].xValue ?? Number.MAX_SAFE_INTEGER,
      completedPoints[0].xValue ?? Number.MAX_SAFE_INTEGER,
    );

    if (startTimestamp === Number.MAX_SAFE_INTEGER) return [];

    return bucketizeHuntProgressData(
      startTimestamp,
      FIVE_MINUTES_IN_SECONDS,
      totalClients,
      scheduledPoints,
      completedPoints,
    );
  }
}
