import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatListModule} from '@angular/material/list';
import {RouterModule} from '@angular/router';

import {HumanReadableSizeModule} from '../human_readable_size/module';
import {TimestampModule} from '../timestamp/module';

import {ClientDetails} from './client_details';
import {ClientDetailsRoutingModule} from './routing';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    CommonModule,
    RouterModule,
    ClientDetailsRoutingModule,
    MatIconModule,
    TimestampModule,
    HumanReadableSizeModule,
    MatDividerModule,
    MatChipsModule,
    MatListModule,
    MatButtonModule,
  ],
  declarations: [
    ClientDetails,
  ],
})
export class ClientDetailsModule {
}
