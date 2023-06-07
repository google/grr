import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyMenuModule} from '@angular/material/legacy-menu';

import {ExpandableHash} from './expandable_hash';


@NgModule({
  imports: [
    CommonModule,
    ClipboardModule,
    MatLegacyButtonModule,
    MatLegacyMenuModule,
    MatIconModule,
  ],
  declarations: [
    ExpandableHash,
  ],
  exports: [
    ExpandableHash,
  ]
})
export class ExpandableHashModule {
}
