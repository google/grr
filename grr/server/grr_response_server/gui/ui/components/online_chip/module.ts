import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';

import {OnlineChip} from './online_chip';

/**
 * Module for a material status chip
 */
@NgModule({
  imports: [
    CommonModule,
    MatChipsModule,
    MatIconModule,
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
