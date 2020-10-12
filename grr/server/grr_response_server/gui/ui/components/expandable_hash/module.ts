import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ExpandableHash } from './expandable_hash'
import { HashesModule } from '../hashes/module'


@NgModule({
  imports: [
    CommonModule,
    HashesModule,
  ],
  declarations: [
    ExpandableHash,
  ],
  exports: [
    ExpandableHash,
  ]
})
export class HashModule { }
