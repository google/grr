import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyDialogModule} from '@angular/material/legacy-dialog';
import {MatLegacyListModule} from '@angular/material/legacy-list';
import {RouterModule} from '@angular/router';

import {CopyButtonModule} from '../helpers/copy_button/copy_button_module';
import {HumanReadableSizeModule} from '../human_readable_size/module';
import {TimestampModule} from '../timestamp/module';

import {ClientDetails} from './client_details';
import {EntryHistoryButtonModule} from './entry_history_button/module';
import {EntryHistoryDialog} from './entry_history_dialog/entry_history_dialog';
import {EntryHistoryDialogModule} from './entry_history_dialog/module';
import {InterfacesDetailsModule} from './interfaces_details/module';
import {ClientDetailsRoutingModule} from './routing';
import {UsersDetailsModule} from './users_details/module';
import {VolumesDetailsModule} from './volumes_details/module';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    CommonModule,
    RouterModule,
    MatLegacyButtonModule,
    MatLegacyChipsModule,
    MatLegacyDialogModule,
    MatDividerModule,
    MatIconModule,
    MatLegacyListModule,
    ClientDetailsRoutingModule,
    CopyButtonModule,
    EntryHistoryButtonModule,
    EntryHistoryDialogModule,
    HumanReadableSizeModule,
    InterfacesDetailsModule,
    TimestampModule,
    UsersDetailsModule,
    VolumesDetailsModule,
  ],
  declarations: [
    ClientDetails,
  ],
  exports: [
    ClientDetails,
  ]
})
export class ClientDetailsModule {
}
