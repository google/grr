import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyDialogModule} from '@angular/material/legacy-dialog';
import {MatLegacyListModule} from '@angular/material/legacy-list';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {RouterModule} from '@angular/router';

import {FlowDetailsModule} from '../../../flow_details/module';
import {TimestampModule} from '../../../timestamp/module';

import {HuntResultDetails} from './hunt_result_details';
import {HuntResultDetailsRoutingModule} from './routing';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    CommonModule,
    FlowDetailsModule,
    RouterModule,
    MatLegacyButtonModule,
    MatLegacyChipsModule,
    MatLegacyDialogModule,
    MatDividerModule,
    MatIconModule,
    MatLegacyListModule,
    MatLegacyProgressSpinnerModule,
    HuntResultDetailsRoutingModule,
    TimestampModule,
  ],
  declarations: [
    HuntResultDetails,
  ],
  exports: [
    HuntResultDetails,
  ]
})
export class HuntResultDetailsModule {
}
