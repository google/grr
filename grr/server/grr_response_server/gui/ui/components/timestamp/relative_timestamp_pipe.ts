import {Pipe, PipeTransform} from '@angular/core';
import {DateTime} from 'luxon';

@Pipe({
  name: 'relativeTimestamp'
})
export class RelativeTimestampPipe implements PipeTransform {
  readonly oneDay = 86400000; // One day in millis
  readonly oneHour = 3600000; // One hour in millis
  readonly oneMin = 60000; // One minute in millis
  readonly oneSecond = 1000; // One second in millis

  transform(jsDate: Date, absoluteOnly: boolean): any {
    if (jsDate === undefined) {
      return "-";
    }

    const date = DateTime.fromJSDate(jsDate);

    if (absoluteOnly) {
      return this.getAbsoluteTimestamp(date);
    }

    const now = DateTime.local();
    const timeElapsed = now.diff(date, "milliseconds").as("milliseconds");

    if (timeElapsed < this.oneMin / 2) {
      return "Just now";
    }

    if (timeElapsed < this.oneMin) {
      return Math.floor(timeElapsed / this.oneSecond) + " seconds ago";
    }

    if (timeElapsed < this.oneHour) {
      return Math.floor(timeElapsed / this.oneMin) + "min ago";
    }

    if (timeElapsed < this.oneDay) {
      return Math.floor(timeElapsed / this.oneHour) + "h" +
        Math.floor((timeElapsed % this.oneHour) / this.oneMin) + "min ago";
    }

    if (now.startOf("day").diff(date, "milliseconds").as("milliseconds") < this.oneDay) {
      return "yesterday at " + date.toLocaleString(DateTime.TIME_24_SIMPLE);
    }

    return this.getAbsoluteTimestamp(date);
  }

  getAbsoluteTimestamp(date: DateTime): any {
    return date.toLocaleString(DateTime.DATETIME_MED);
  }
}
