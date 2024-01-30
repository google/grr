import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatMenuModule} from '@angular/material/menu';

import {ExpandableHash} from './expandable_hash';

@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    ClipboardModule,
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    // keep-sorted end
  ],
  declarations: [ExpandableHash],
  exports: [ExpandableHash],
})
export class ExpandableHashModule {}
