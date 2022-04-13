import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatDialogModule} from '@angular/material/dialog';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatSnackBarModule} from '@angular/material/snack-bar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {RouterModule} from '@angular/router';

import {ApprovalChipModule} from '../client/approval_chip/approval_chip_module';
import {ClientAddLabelDialogModule} from '../client_add_label_dialog/module';
import {CopyButtonModule} from '../helpers/copy_button/copy_button_module';
import {DrawerLinkModule} from '../helpers/drawer_link/drawer_link_module';
import {OnlineChipModule} from '../online_chip/module';
import {TimestampModule} from '../timestamp/module';

import {ClientOverview} from './client_overview';

/**
 * Module for the client overview component.
 */
@NgModule({
  imports: [
    ClipboardModule,
    CommonModule,
    RouterModule,

    MatButtonModule,
    MatChipsModule,
    MatDialogModule,
    MatDividerModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,

    ApprovalChipModule,
    CopyButtonModule,
    DrawerLinkModule,
    ClientAddLabelDialogModule,
    OnlineChipModule,
    TimestampModule,
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
