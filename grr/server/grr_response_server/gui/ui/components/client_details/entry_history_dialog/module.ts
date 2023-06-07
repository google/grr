import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyDialogModule} from '@angular/material/legacy-dialog';

import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {TimestampModule} from '../../timestamp/module';
import {InterfacesDetailsModule} from '../interfaces_details/module';
import {UsersDetailsModule} from '../users_details/module';
import {VolumesDetailsModule} from '../volumes_details/module';

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
    MatLegacyDialogModule,
    MatLegacyButtonModule,
    UsersDetailsModule,
    VolumesDetailsModule,
    InterfacesDetailsModule,
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
