import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyDialogModule} from '@angular/material/legacy-dialog';

import {EntryHistoryDialogModule} from '../entry_history_dialog/module';

import {EntryHistoryButton} from './entry_history_button';

/**
 * Module for the entry history button component.
 */
@NgModule({
  imports: [
    CommonModule,
    MatLegacyButtonModule,
    MatLegacyDialogModule,
    EntryHistoryDialogModule,
  ],
  declarations: [
    EntryHistoryButton,
  ],
  exports: [
    EntryHistoryButton,
  ]
})
export class EntryHistoryButtonModule {
}
