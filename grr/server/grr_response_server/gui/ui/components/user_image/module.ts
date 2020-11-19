import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';

import {UserImage} from './user_image';

/** Module for UserImage and related code. */
@NgModule({
  imports: [
    CommonModule,
    MatIconModule,
  ],
  declarations: [
    UserImage,
  ],
  exports: [
    UserImage,
  ],
})
export class UserImageModule {
}
