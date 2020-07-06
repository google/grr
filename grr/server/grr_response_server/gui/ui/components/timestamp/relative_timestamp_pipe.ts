import {Pipe, PipeTransform} from '@angular/core';
import {DateTime} from 'luxon';

@Pipe({
  name: 'relativeTimestamp'
})
export class RelativeTimestampPipe implements PipeTransform {
  private static readonly ONE_DAY_IN_MILLIS = 86400000;
  private static readonly ONE_HOUR_IN_MILLIS = 3600000;
  private static readonly ONE_MIN_IN_MILLIS = 60000;
  private static readonly ONE_SECOND_IN_MILLIS = 1000;

  transform(jsDate: Date, absoluteOnly: boolean): string {
    if (jsDate === undefined) {
      return '-';
    }

    const date = DateTime.fromJSDate(jsDate);

    if (absoluteOnly) {
      return this.getAbsoluteTimestamp(date);
    }

    const now = DateTime.local();
    const timeElapsed = now.diff(date, 'milliseconds').as('milliseconds');

    if (timeElapsed < RelativeTimestampPipe.ONE_MIN_IN_MILLIS / 2) {
      return "Just now";
    }

    if (timeElapsed < RelativeTimestampPipe.ONE_MIN_IN_MILLIS) {
      return `${Math.floor(timeElapsed / RelativeTimestampPipe.ONE_SECOND_IN_MILLIS)} seconds ago`;
    }

    if (timeElapsed < RelativeTimestampPipe.ONE_HOUR_IN_MILLIS) {
      return `${Math.floor(timeElapsed / RelativeTimestampPipe.ONE_MIN_IN_MILLIS)}min ago`;
    }

    if (timeElapsed < RelativeTimestampPipe.ONE_DAY_IN_MILLIS) {
      let timeDiff = now.diff(date, ['hours', 'minutes']);

      return `${timeDiff.hours}h${Math.floor(timeDiff.minutes)}min ago`
    }

    let yesterdayDate = now.minus({days: 1});
    if (yesterdayDate.hasSame(date, 'year') && yesterdayDate.hasSame(date, 'month') &&
      yesterdayDate.hasSame(date, 'day')) {
      return `yesterday at ${date.toLocaleString(DateTime.TIME_24_SIMPLE)}`;
    }

    return this.getAbsoluteTimestamp(date);
  }

  getAbsoluteTimestamp(date: DateTime): any {
    return date.toLocaleString(DateTime.DATETIME_MED);
  }
}
