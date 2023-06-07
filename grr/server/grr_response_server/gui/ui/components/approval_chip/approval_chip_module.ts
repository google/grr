import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';

import {ApprovalChip} from './approval_chip';

@NgModule({
  imports: [CommonModule, MatLegacyChipsModule, MatIconModule],
  declarations: [ApprovalChip],
  exports: [ApprovalChip]
})
export class ApprovalChipModule {
}
