import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';

import {OnlineChip} from './online_chip';

/**
 * Module for a material status chip
 */
@NgModule({
  imports: [
    CommonModule,
    MatLegacyChipsModule,
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
