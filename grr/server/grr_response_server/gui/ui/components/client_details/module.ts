import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatDialogModule} from '@angular/material/dialog';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatListModule} from '@angular/material/list';
import {RouterModule} from '@angular/router';

import {HumanReadableSizeModule} from '../human_readable_size/module';
import {TimestampModule} from '../timestamp/module';

import {ClientDetails} from './client_details';
import {EntryHistoryButton} from './entry_history_button/entry_history_button';
import {EntryHistoryDialog} from './entry_history_dialog/entry_history_dialog';
import {VolumesDetails} from './volumes_details/volumes_details';
import {UsersDetails} from './users_details/users_details';
import {InterfaceDetails as InterfacesDetails} from './interfaces_details/interfaces_details';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    CommonModule,
    RouterModule,
    MatIconModule,
    TimestampModule,
    HumanReadableSizeModule,
    MatDividerModule,
    MatChipsModule,
    MatListModule,
    MatButtonModule,
    MatDialogModule,
  ],
  declarations: [
    ClientDetails,
    EntryHistoryDialog,
    EntryHistoryButton,
    VolumesDetails,
    UsersDetails,
    InterfacesDetails,
  ],
  exports: [
    ClientDetails,
  ]
})
export class ClientDetailsModule {
}
