import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {MatDialog} from '@angular/material/dialog';
import {Client} from '@app/lib/models/client';
import {Observable} from 'rxjs';

import {EntryHistoryDialog, EntryHistoryDialogParams} from '../entry_history_dialog/entry_history_dialog';
import {ClientPageFacade} from '@app/store/client_page_facade';
import {getClientEntriesChanged} from '../client_diff';
import {map} from 'rxjs/operators';

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

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
      private readonly dialog: MatDialog,
  ) {}

  // TODO move this to ClientDetailsStore
  readonly clientEntryChanges$ =
      this.clientPageFacade.selectedClientVersions$.pipe(
          map(getClientEntriesChanged),
      );

  openEntryHistoryDialog(clientVersions: Client[]) {
    const data: EntryHistoryDialogParams = {
      path: this.path,
      clientVersions,
    };

    this.dialog.open(EntryHistoryDialog, {data});
  }
}
