import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';

import {Client} from '../../../lib/models/client';
import {ClientDetailsGlobalStore} from '../../../store/client_details_global_store';
import {EntryHistoryDialog, EntryHistoryDialogParams, EntryType} from '../entry_history_dialog/entry_history_dialog';

/**
 * Component displaying a button with the associated entry changes,
 * only when there is at least one change
 */
@Component({
  selector: 'entry-history-button',
  templateUrl: './entry_history_button.ng.html',
  styleUrls: ['./entry_history_button.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EntryHistoryButton {
  /** The path to the entry. Properties in the path must be separated by "." */
  @Input() path!: string;
  @Input() type: EntryType = 'primitive';

  constructor(
      private readonly clientDetailsGlobalStore: ClientDetailsGlobalStore,
      private readonly dialog: MatDialog,
  ) {}

  readonly clientEntryChanges$ =
      this.clientDetailsGlobalStore.selectedClientEntriesChanged$;

  openEntryHistoryDialog(clientVersions: ReadonlyArray<Client>) {
    const data: EntryHistoryDialogParams = {
      path: this.path.split('.'),
      clientVersions,
      type: this.type,
    };

    this.dialog.open(EntryHistoryDialog, {data});
  }
}
