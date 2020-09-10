import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {UsersDetails} from './users_details';
import {TimestampModule} from '@app/components/timestamp/module';

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
