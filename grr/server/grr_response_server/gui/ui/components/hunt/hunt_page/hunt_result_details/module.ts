import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatDialogModule} from '@angular/material/dialog';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {RouterModule} from '@angular/router';

import {FlowDetailsModule} from '../../../flow_details/module';
import {TimestampModule} from '../../../timestamp/module';

import {HuntResultDetails} from './hunt_result_details';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    CommonModule,
    FlowDetailsModule,
    MatButtonModule,
    MatChipsModule,
    MatDialogModule,
    MatDividerModule,
    MatIconModule,
    MatProgressSpinnerModule,
    RouterModule,
    TimestampModule,
    // keep-sorted end
  ],
  declarations: [HuntResultDetails],
  exports: [HuntResultDetails],
})
export class HuntResultDetailsModule {}
