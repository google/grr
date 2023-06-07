import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyDialogModule} from '@angular/material/legacy-dialog';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {MatLegacySnackBarModule} from '@angular/material/legacy-snack-bar';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
import {RouterModule} from '@angular/router';

import {SanitizerPipeModule} from '../../pipes/sanitizer/module';
import {ApprovalChipModule} from '../approval_chip/approval_chip_module';
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

    MatLegacyButtonModule,
    MatLegacyCardModule,
    MatLegacyChipsModule,
    MatLegacyDialogModule,
    MatDividerModule,
    MatIconModule,
    MatLegacyProgressSpinnerModule,
    MatLegacySnackBarModule,
    MatLegacyTooltipModule,

    ApprovalChipModule,
    CopyButtonModule,
    DrawerLinkModule,
    ClientAddLabelDialogModule,
    OnlineChipModule,
    TimestampModule,
    SanitizerPipeModule,
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
