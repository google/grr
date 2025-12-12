import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import {MatTableModule} from '@angular/material/table';
import {MatTooltipModule} from '@angular/material/tooltip';
import {RouterModule} from '@angular/router';

import {ClientSnapshot} from '../../../lib/models/client';
import {Timestamp} from '../../shared/timestamp';

/** Data passed to the dialog. */
export interface SnapshotEntryHistoryDialogData {
  snapshots: readonly ClientSnapshot[];
  entryAccessor: (client: ClientSnapshot) => string;
}

/**
 * Component displaying a button with the associated entry changes,
 * only when there is at least one change
 */
@Component({
  selector: 'snapshot-entry-history-dialog',
  templateUrl: './snapshot_entry_history_dialog.ng.html',
  styleUrls: ['./snapshot_entry_history_dialog.scss'],
  imports: [
    CommonModule,
    MatDialogModule,
    MatTableModule,
    MatTooltipModule,
    Timestamp,
    RouterModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SnapshotEntryHistoryDialog {
  protected readonly dialogRef = inject(
    MatDialogRef<SnapshotEntryHistoryDialog>,
  );
  readonly dialogData = inject<SnapshotEntryHistoryDialogData>(MAT_DIALOG_DATA);

  displayedColumns: string[] = ['timestamp', 'value'];
}
