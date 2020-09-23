import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatDialogModule} from '@angular/material/dialog';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatSnackBarModule} from '@angular/material/snack-bar';

import {ClientAddLabelDialogModule} from '../client_add_label_dialog/module';
import {OnlineChipModule} from '../online_chip/module';
import {TimestampModule} from '../timestamp/module';

import {ClientOverview} from './client_overview';

/**
 * Module for the client overview component.
 */
@NgModule({
  imports: [
    CommonModule,
    MatIconModule,
    TimestampModule,
    MatDividerModule,
    MatChipsModule,
    MatButtonModule,
    ClientAddLabelDialogModule,
    OnlineChipModule,
    MatSnackBarModule,
    MatDialogModule,
    ClipboardModule,
  ],
  declarations: [
    ClientOverview,
  ],
  exports: [
    ClientOverview,
  ]
})
export class ClientOverviewModule {
}
