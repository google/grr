import {Component, Inject} from '@angular/core';
import {MAT_DIALOG_DATA} from '@angular/material/dialog';
import {Client} from '../../../lib/models/client';

/** Entry type */
export type EntryType =
    'primitive'|'timestamp'|'size'|'user-list'|'interface-list'|'volume-list';

/** Parameters required to open an EntryHistoryDialog */
export interface EntryHistoryDialogParams {
  readonly path: ReadonlyArray<string>;
  readonly type: EntryType;
  readonly clientVersions: ReadonlyArray<Client>;
}

interface EntryHistoryTableRow<T> {
  time?: Date;
  version: T;
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
  // tslint:disable-next-line:no-any
  readonly tableRows: Array<EntryHistoryTableRow<any>> = [];

  constructor(
      @Inject(MAT_DIALOG_DATA) private readonly data: EntryHistoryDialogParams,
  ) {
    if (this.data.path.length === 0) {
      throw new Error('Empty "path" provided');
    }
    this.entryType = data.type;
    this.initTableRows(this.data);
  }

  private initTableRows(data: EntryHistoryDialogParams) {
    data.clientVersions.forEach((client) => {
      // tslint:disable-next-line:no-any
      let property: any = client;
      data.path.forEach((token) => {
        if (token === '' || property === undefined) {
          throw new Error(`Wrong "path" provided: ${data.path}`);
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
