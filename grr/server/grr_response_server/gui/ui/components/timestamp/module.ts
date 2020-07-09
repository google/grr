import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {Timestamp} from './timestamp';
import {RelativeTimestampPipe} from './relative_timestamp_pipe';
import {MatTooltipModule} from '@angular/material/tooltip';
import {MatIconModule} from '@angular/material/icon';
import {MatButtonModule} from '@angular/material/button';
import {ClipboardModule} from '@angular/cdk/clipboard';

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
