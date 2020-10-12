import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Hashes } from './hashes'



@NgModule({
  imports: [
    CommonModule,
  ],
  declarations: [
    Hashes,
  ],
  exports: [
    Hashes,
  ]
})
export class HashesModule { }
