import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatDialogModule} from '@angular/material/dialog';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatListModule} from '@angular/material/list';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {RouterModule} from '@angular/router';

import {TimestampModule} from '../../../timestamp/module';

import {HuntResultDetails} from './hunt_result_details';
import {HuntResultDetailsRoutingModule} from './routing';

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
    MatProgressSpinnerModule,
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
