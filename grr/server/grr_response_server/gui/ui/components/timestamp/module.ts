import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';

import {RelativeTimestampPipe} from './relative_timestamp_pipe';
import {Timestamp} from './timestamp';

/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    // Angular builtin modules.
    CommonModule,
    MatTooltipModule,
    MatIconModule,
    MatButtonModule,
    ClipboardModule,
  ],
  declarations: [
    Timestamp,
    RelativeTimestampPipe,
  ],
  exports: [
    Timestamp,
    RelativeTimestampPipe,
  ],
})
export class TimestampModule {
}
