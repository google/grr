import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';

import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {TimestampModule} from '../../timestamp/module';

import {UsersDetails} from './users_details';

/**
 * Module for the users details component.
 */
@NgModule({
  imports: [
    CommonModule,
    CopyButtonModule,
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
