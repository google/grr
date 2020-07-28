import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';
import {ClientDetails} from './client_details';
import {ClientDetailsRoutingModule} from './routing';
import {MatIconModule} from '@angular/material/icon';
import {CommonModule} from '@angular/common';
import {TimestampModule} from '../timestamp/module';
import {HumanReadableSizeModule} from '../human_readable_size/module';


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
  ],
  declarations: [
    ClientDetails,
  ],
})
export class ClientDetailsModule {
}
