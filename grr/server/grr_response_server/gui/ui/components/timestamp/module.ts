import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';
import {Subject} from 'rxjs';

import {CopyButtonModule} from '../helpers/copy_button/copy_button_module';

import {Timestamp, TimestampRefreshTimer} from './timestamp';

/**
 * Module for the Timestamp component.
 */
@NgModule({
  imports: [
    // Angular builtin modules.
    CommonModule,
    MatTooltipModule,
    MatIconModule,
    MatButtonModule,
    ClipboardModule,
    CopyButtonModule,
  ],
  declarations: [
    Timestamp,
  ],
  exports: [
    Timestamp,
  ],
})
export class TimestampModule {
}

/**
 * Module that mocks the Timestamp's timer to prevent timer problems, e.g.
 * "Timeout - Async function did not complete within 5000ms".
 */
@NgModule({
  providers: [
    {
      provide: TimestampRefreshTimer,
      useFactory: () => ({timer$: new Subject<void>()}),
    },
  ],
})
export class TimestampTestingModule {
}
