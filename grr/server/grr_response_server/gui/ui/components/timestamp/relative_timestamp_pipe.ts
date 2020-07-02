import {Pipe, PipeTransform} from '@angular/core';
import {DatePipe} from '@angular/common';

@Pipe({
  name: 'relativeTimestamp'
})
export class RelativeTimestampPipe extends
  DatePipe implements PipeTransform {

  readonly oneDay = 86400000; // One day in millis
  readonly oneHour = 3600000; // One hour in millis
  readonly oneMin = 60000; // One minute in millis

  transform(date: Date, absoluteOnly: any): any {
    if (date === undefined) {
      return "-";
    }

    if (absoluteOnly) {
      return this.getAbsoluteTimestamp(date);
    }

    var currentDate = new Date();
    var timeDifference = currentDate.getTime() - date.getTime();
    var relativeDate = new Date();
    relativeDate.setTime(timeDifference);

    if (timeDifference < this.oneMin / 2) {
      return "Just now";
    }

    if (timeDifference < this.oneHour) {
      return super.transform(relativeDate, "m'min ago'");
    }

    if (timeDifference < this.oneDay) {
      return super.transform(relativeDate, "H'h'm'min ago'");
    }

    if (timeDifference < this.oneDay * 2) {
      return super.transform(date, "'yesterday at' HH':'mm");
    }

    return this.getAbsoluteTimestamp(date);
  }

  getAbsoluteTimestamp(date: Date): any {
    return super.transform(date, "MMM d \''yy 'at' HH:mm");
  }
}
