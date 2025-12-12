import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, effect, input} from '@angular/core';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatTooltipModule} from '@angular/material/tooltip';

import {ApiGetHuntClientCompletionStatsResult} from '../../../lib/api/api_interfaces';
import {Timestamp} from '../../shared/timestamp';

const COLUMNS = ['timestamp', 'completedClients', 'scheduledClients'];

interface ProgressData {
  timestamp: number;
  completedClients: bigint;
  scheduledClients: bigint;
}

function toProgressData(
  progress: ApiGetHuntClientCompletionStatsResult | null | undefined,
): ProgressData[] {
  if (!progress) return [];

  if (progress.startPoints?.length !== progress.completePoints?.length) {
    throw new Error(
      'Timestamps for progress table do not match. This should never happen.',
    );
  }
  return (
    progress.startPoints?.map((startPoint, index) => {
      const completePoint = progress.completePoints![index];
      if (completePoint.xValue !== startPoint.xValue) {
        throw new Error(
          'Timestamps for progress table do not match. This should never happen.',
        );
      }
      return {
        timestamp: startPoint.xValue! * 1000,
        completedClients: BigInt(completePoint.yValue!),
        scheduledClients: BigInt(startPoint.yValue!),
      };
    }) ?? []
  );
}

/** Provides client completion progress data for a Hunt in table format. */
@Component({
  selector: 'fleet-collection-progress-table',
  templateUrl: './fleet_collection_progress_table.ng.html',
  imports: [CommonModule, MatTableModule, MatTooltipModule, Timestamp],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionProgressTable {
  readonly collectionProgressData = input.required<
    ProgressData[],
    ApiGetHuntClientCompletionStatsResult | null | undefined
  >({
    transform: toProgressData,
  });
  totalClients = input.required<bigint | null | undefined>();

  readonly dataSource = new MatTableDataSource<ProgressData>();
  readonly columns = COLUMNS;

  constructor() {
    effect(() => {
      this.dataSource.data = this.collectionProgressData().slice();
    });
  }

  protected getPercentage(part: bigint): bigint {
    const totalClients = this.totalClients();
    if (!totalClients || totalClients === BigInt(0)) {
      return BigInt(0);
    }

    return (part * BigInt(100)) / totalClients;
  }
}
