import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';

import {TimestampModule} from '../../timestamp/module';

import {UsersDetails} from './users_details';

/**
 * Module for the users details component.
 */
@NgModule({
  imports: [
    CommonModule,
    TimestampModule,
  ],
  declarations: [
    UsersDetails,
  ],
  exports: [
    UsersDetails,
  ]
})
export class UsersDetailsModule {
}
