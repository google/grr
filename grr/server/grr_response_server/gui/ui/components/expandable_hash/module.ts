import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ExpandableHash } from './expandable_hash'
import { Hashes } from './hashes/hashes'
import { OverlayModule } from '@angular/cdk/overlay';
import { ClipboardModule } from '@angular/cdk/clipboard';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';


@NgModule({
  imports: [
    CommonModule,
    OverlayModule,
    ClipboardModule,
    MatIconModule,
    MatButtonModule,
  ],
  declarations: [
    ExpandableHash,
    Hashes,
  ],
  exports: [
    ExpandableHash,
  ]
})
export class ExpandableHashModule { }
