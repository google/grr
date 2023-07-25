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
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    CommonModule,
    MatChipsModule,
    MatIconModule,
    // keep-sorted end
    // clang-format on
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
