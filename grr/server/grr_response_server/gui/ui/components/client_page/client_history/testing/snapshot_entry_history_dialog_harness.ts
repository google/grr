import {MatDialogHarness} from '@angular/material/dialog/testing';
import {MatTableHarness} from '@angular/material/table/testing';

/** Harness for the SnapshotEntryHistory Dialog. */
export class SnapshotEntryHistoryDialogHarness extends MatDialogHarness {
  static override hostSelector = 'snapshot-entry-history-dialog';

  readonly table = this.locatorFor(MatTableHarness);
}
