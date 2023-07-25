import {CommonModule} from '@angular/common';
import {Component, Input} from '@angular/core';
import {MatTableModule} from '@angular/material/table';
import {MatTooltipModule} from '@angular/material/tooltip';

import {HuntCompletionProgressTableRow} from '../../../../lib/models/hunt';
import {TimestampModule} from '../../../timestamp/module';

// Order of the columns is important
const HUNT_PROGRESS_TABLE_COLUMN_DEFS =
    ['timestamp', 'completedClients', 'scheduledClients'];

/** Provides client completion progress data for a Hunt in table format. */
@Component({
  selector: 'app-hunt-progress-table',
  templateUrl: './hunt_progress_table.ng.html',
  styleUrls: ['./hunt_progress_table.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatTooltipModule,
    TimestampModule,
  ],
})
export class HuntProgressTable {
  @Input()
  set completionProgressData(progressData: HuntCompletionProgressTableRow[]|
                             null|undefined) {
    this.safeCompletionProgressData = progressData ?? [];
  }
  @Input() totalClients: bigint|null|undefined;

  readonly columnDefs = HUNT_PROGRESS_TABLE_COLUMN_DEFS;

  safeCompletionProgressData: HuntCompletionProgressTableRow[] = [];

  trackByTimestamp(index: number, item: HuntCompletionProgressTableRow):
      number {
    return item.timestamp;
  }
}