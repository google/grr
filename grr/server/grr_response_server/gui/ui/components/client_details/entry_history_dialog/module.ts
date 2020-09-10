import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule} from '@angular/material/dialog';
import {MatIconModule} from '@angular/material/icon';

import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {TimestampModule} from '../../timestamp/module';

import {EntryHistoryDialog} from './entry_history_dialog';

/**
 * Module for the entry history dialog component.
 */
@NgModule({
  imports: [
    CommonModule,
    MatIconModule,
    TimestampModule,
    HumanReadableSizeModule,
    MatDialogModule,
    MatButtonModule,
  ],
  declarations: [
    EntryHistoryDialog,
  ],
  exports: [
    EntryHistoryDialog,
  ]
})
export class EntryHistoryDialogModule {
}
