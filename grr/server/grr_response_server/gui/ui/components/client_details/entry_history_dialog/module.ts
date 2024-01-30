import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule} from '@angular/material/dialog';
import {MatIconModule} from '@angular/material/icon';

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
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    CommonModule,
    HumanReadableSizeModule,
    InterfacesDetailsModule,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    TimestampModule,
    UsersDetailsModule,
    VolumesDetailsModule,
    // keep-sorted end
  ],
  declarations: [EntryHistoryDialog],
  exports: [EntryHistoryDialog],
})
export class EntryHistoryDialogModule {}
