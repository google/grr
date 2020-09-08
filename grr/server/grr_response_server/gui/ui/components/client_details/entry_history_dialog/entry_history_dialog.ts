import {Component, Inject} from '@angular/core';
import {MAT_DIALOG_DATA} from '@angular/material/dialog';
import {Client} from '@app/lib/models/client';

/** Entry type */
export type EntryType =
    'primitive'|'timestamp'|'size'|'user-list'|'interface-list'|'volume-list';

/** Parameters required to open an EntryHistoryDialog */
export interface EntryHistoryDialogParams {
  readonly path: string;
  readonly type: EntryType;
  readonly clientVersions: ReadonlyArray<Client>;
}

interface EntryHistoryTableRow {
  time: Date;
  version: any;
}

/**
 * Component displaying the entry history dialog.
 */
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

  private initTableRows(data: EntryHistoryDialogParams) {
    data.clientVersions.forEach((client) => {
      let property: any = client;
      data.path.split('.').forEach((token) => {
        if (token === '' || property === undefined) {
          throw new Error(`Wrong "path" provided: ${this.data.path}`);
        }
        property = property[token];
      });


      this.tableRows.push({
        time: client.age,
        version: property,
      });
    });
  }
}
