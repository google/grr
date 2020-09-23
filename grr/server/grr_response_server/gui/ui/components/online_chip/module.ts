import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatChipsModule} from '@angular/material/chips';

import {OnlineChip} from './online_chip';

/**
 * Module for a material status chip
 */
@NgModule({
  imports: [
    CommonModule,
    MatChipsModule,
  ],
  declarations: [
    OnlineChip,
  ],
  exports: [
    OnlineChip,
  ],
})
export class OnlineChipModule {
}
