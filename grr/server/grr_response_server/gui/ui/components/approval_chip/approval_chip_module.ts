import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';

import {ApprovalChip} from './approval_chip';

@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    CommonModule,
    MatChipsModule,
    MatIconModule,
    // keep-sorted end
  ],
  declarations: [ApprovalChip],
  exports: [ApprovalChip],
})
export class ApprovalChipModule {}
