import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ExpandableHash } from './expandable_hash'
import { ClipboardModule } from '@angular/cdk/clipboard';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatIconModule } from '@angular/material/icon';


@NgModule({
  imports: [
    CommonModule,
    ClipboardModule,
    MatButtonModule,
    MatMenuModule,
    MatIconModule,
  ],
  declarations: [
    ExpandableHash,
  ],
  exports: [
    ExpandableHash,
  ]
})
export class ExpandableHashModule { }
