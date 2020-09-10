import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule} from '@angular/material/dialog';

import {EntryHistoryButton} from './entry_history_button';

/**
 * Module for the entry history button component.
 */
@NgModule({
  imports: [
    CommonModule,
    MatButtonModule,
    MatDialogModule,
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
