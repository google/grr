import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {Timestamp} from './timestamp';
import {RelativeTimestampPipe} from './relative_timestamp_pipe';
import {MatTooltipModule} from '@angular/material/tooltip';

/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    // Angular builtin modules.
    CommonModule,
    MatTooltipModule
  ],
  declarations: [
    Timestamp,
    RelativeTimestampPipe
  ],
  exports: [
    Timestamp,
    RelativeTimestampPipe
  ],
})
export class TimestampModule {
}
