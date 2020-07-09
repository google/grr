import {Pipe, PipeTransform} from '@angular/core';
import {DateTime} from 'luxon';

@Pipe({
  name: 'relativeTimestamp'
})
export class RelativeTimestampPipe implements PipeTransform {
  private static readonly UNDEFINED_TIMESTAMP = '-';

  transform(jsDate: Date): string {
    const date = DateTime.fromJSDate(jsDate);
    const relativeTimestamp = date.toRelative();

    if (relativeTimestamp === null) {
      return RelativeTimestampPipe.UNDEFINED_TIMESTAMP;
    }

    return relativeTimestamp;
  }
}
