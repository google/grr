import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {RouterModule} from '@angular/router';

import {InfiniteList} from './infinite_list';

/**
 * Module for the InfiniteList component.
 */
@NgModule({
  imports: [
    CommonModule,
    RouterModule,
    MatLegacyProgressSpinnerModule,
    MatLegacyButtonModule,
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
