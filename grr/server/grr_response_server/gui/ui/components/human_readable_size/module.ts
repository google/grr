import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {HumanReadableSizeComponent} from './human_readable_size';

/**
 * Module for the human readable size component.
 */
@NgModule({
  imports: [
    CommonModule,
  ],
  declarations: [
    HumanReadableSizeComponent,
  ],
  exports: [
    HumanReadableSizeComponent,
  ],
})
export class HumanReadableSizeModule {
}
