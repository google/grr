import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';

import {HuntStatusChip} from './hunt_status_chip';

@NgModule({
  imports: [
    CommonModule,
    MatLegacyChipsModule,
    MatIconModule,
    MatLegacyProgressSpinnerModule,
    MatLegacyTooltipModule,
  ],
  declarations: [HuntStatusChip],
  exports: [HuntStatusChip]
})
export class HuntStatusChipModule {
}
