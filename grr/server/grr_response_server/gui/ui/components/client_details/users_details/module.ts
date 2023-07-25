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
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    CommonModule,
    CopyButtonModule,
    TimestampModule,
    // keep-sorted end
    // clang-format on
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
