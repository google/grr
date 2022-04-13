import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatDialogModule} from '@angular/material/dialog';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatListModule} from '@angular/material/list';
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

    MatButtonModule,
    MatChipsModule,
    MatDialogModule,
    MatDividerModule,
    MatIconModule,
    MatListModule,

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
  entryComponents: [
    EntryHistoryDialog,
  ],
  exports: [
    ClientDetails,
  ]
})
export class ClientDetailsModule {
}
