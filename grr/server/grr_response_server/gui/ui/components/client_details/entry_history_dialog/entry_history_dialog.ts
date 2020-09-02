import {Component, Inject} from '@angular/core';
import {MAT_DIALOG_DATA} from '@angular/material/dialog';
import {Client} from '@app/lib/models/client';

export type EntryType =
    'primitive'|'timestamp'|'size'|'user-list'|'interface-list'|'volume-list';

export interface EntryHistoryDialogParams {
  path: string;
  type: EntryType;
  clientVersions: Client[];
}

interface EntryHistoryTableRow {
  time: Date;
  version: any;
}

@Component({
  selector: 'entry-history-dialog',
  templateUrl: './entry_history_dialog.ng.html',
  styleUrls: ['./entry_history_dialog.scss'],
})
export class EntryHistoryDialog {
  readonly entryType: EntryType;
  readonly tableRows: EntryHistoryTableRow[] = [];

  constructor(@Inject(MAT_DIALOG_DATA) private readonly data:
                  EntryHistoryDialogParams) {
    this.entryType = data.type;
    this.initTableRows(this.data);
  }

  initTableRows(data: EntryHistoryDialogParams) {
    data.clientVersions.forEach((client) => {
      let property: any = client;
      data.path.split('.').forEach((token) => {
        property = property[token];
      });

      this.tableRows?.push({
        time: client.age,
        version: property,
      });
    });
  }
}
