import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';

import {ApprovalChip} from './approval_chip';

@NgModule({
  imports: [CommonModule, MatChipsModule, MatIconModule],
  declarations: [ApprovalChip],
  exports: [ApprovalChip]
})
export class ApprovalChipModule {
}
