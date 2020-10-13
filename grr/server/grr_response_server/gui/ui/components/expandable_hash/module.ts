import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ExpandableHash } from './expandable_hash'
import { Hashes } from './hashes/hashes'
import { OverlayModule } from '@angular/cdk/overlay';


@NgModule({
  imports: [
    CommonModule,
    OverlayModule,
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
