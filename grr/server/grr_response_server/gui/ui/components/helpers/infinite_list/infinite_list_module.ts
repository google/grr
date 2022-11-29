import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {RouterModule} from '@angular/router';

import {InfiniteList} from './infinite_list';

/**
 * Module for the InfiniteList component.
 */
@NgModule({
  imports: [
    CommonModule,
    RouterModule,
    MatProgressSpinnerModule,
    MatButtonModule,
  ],
  declarations: [
    InfiniteList,
  ],
  exports: [
    InfiniteList,
  ],
})
export class InfiniteListModule {
}
