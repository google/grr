import {DatePipe} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  effect,
  input,
  signal,
} from '@angular/core';
import {MatTooltipModule} from '@angular/material/tooltip';

import {DateTime, Duration} from '../../lib/date_time';
import {CopyButton} from './copy_button';

/**
 * The interval in milliseconds to update the relative timestamp.
 */
export const RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS = 1000;

const MINUTE_THRESHOLD = Duration.fromObject({minutes: 1});

function computeRelative(jsDate: Date | null | undefined) {
  if (jsDate == null) {
    return '';
  }

  const date = DateTime.fromJSDate(jsDate);
  const diff = date.diffNow();
  if (!diff.isValid) {
    return '';
  } else if (Math.abs(diff.valueOf()) < MINUTE_THRESHOLD.valueOf()) {
    return 'less than 1 minute ago';
  } else {
    return date.toRelative() ?? '';
  }
}

/**
 * String-based enum that defines the visibility of the relative timestamp (x
 * min ago).
 */
export type RelativeTimestampVisibility = 'visible' | 'tooltip' | 'hidden';

/**
 * Shows a formatted timestamp, based on the date received as parameter.
 */
@Component({
  selector: 'timestamp',
  templateUrl: './timestamp.ng.html',
  styleUrls: ['./timestamp.scss'],
  imports: [CopyButton, DatePipe, MatTooltipModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Timestamp {
  readonly timezone: string = 'UTC';

  protected readonly date = input<Date | undefined>();
  /**
   * Whether the timestamp should be displayed in a single line or allow
   * multiple lines.
   */
  protected readonly multiline = input<boolean | undefined>();
  protected readonly relativeTimestamp =
    input<RelativeTimestampVisibility>('tooltip');

  protected readonly relativeTimestampString = signal('');

  constructor() {
    effect((onCleanup) => {
      const interval = setInterval(() => {
        this.relativeTimestampString.set(computeRelative(this.date()));
      }, RELATIVE_TIMESTAMP_UPDATE_INTERVAL_MS);
      onCleanup(() => {
        clearInterval(interval);
      });
    });
  }
}
