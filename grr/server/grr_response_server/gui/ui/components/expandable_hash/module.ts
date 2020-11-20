import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ExpandableHash } from './expandable_hash'
import { ClipboardModule } from '@angular/cdk/clipboard';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';


@NgModule({
  imports: [
    CommonModule,
    ClipboardModule,
    MatButtonModule,
    MatMenuModule,
  ],
  declarations: [
    ExpandableHash,
  ],
  exports: [
    ExpandableHash,
  ]
})
export class ExpandableHashModule { }
