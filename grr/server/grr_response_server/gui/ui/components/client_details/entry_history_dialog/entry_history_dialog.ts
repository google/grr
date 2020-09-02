import {Component, Inject} from '@angular/core';
import {MAT_DIALOG_DATA} from '@angular/material/dialog';
import {Client} from '@app/lib/models/client';

export interface EntryHistoryDialogParams {
  path: string;
  clientVersions: Client[];
}

interface EntryHistoryTableRow {
  time: Date;
  version: string;
}

@Component({
  selector: 'entry-history-dialog',
  templateUrl: './entry_history_dialog.ng.html',
  styleUrls: ['./entry_history_dialog.scss'],
})
export class EntryHistoryDialog {
  constructor(
      @Inject(MAT_DIALOG_DATA) private readonly history:
          EntryHistoryDialogParams) {}

  entryHistory: EntryHistoryTableRow[] = [
    {time: new Date(), version: 'first version'},
    {time: new Date(), version: 'first version'},
  ];
}
