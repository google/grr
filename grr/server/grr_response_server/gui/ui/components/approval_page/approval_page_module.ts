import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';

import {UserImageModule} from '../user_image/module';

import {ApprovalPage} from './approval_page';
import {ApprovalRoutingModule} from './routing';

@NgModule({
  imports: [
    CommonModule,
    ApprovalRoutingModule,
    MatButtonModule,
    MatCardModule,
    UserImageModule,
  ],
  declarations: [
    ApprovalPage,
  ],
  exports: [
    ApprovalPage,
  ]
})
export class ApprovalPageModule {
}
