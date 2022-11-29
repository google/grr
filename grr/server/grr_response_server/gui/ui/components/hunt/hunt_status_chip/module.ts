import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';

import {HuntStatusChip} from './hunt_status_chip';

@NgModule({
  imports:
      [CommonModule, MatChipsModule, MatIconModule, MatProgressSpinnerModule],
  declarations: [HuntStatusChip],
  exports: [HuntStatusChip]
})
export class HuntStatusChipModule {
}
