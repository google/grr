import {Pipe, PipeTransform} from '@angular/core';
import {toDurationString} from '../../lib/duration_conversion';

/**
 * Pipe that converts number bytes to a human readable format.
 */
@Pipe({name: 'humanReadableDuration'})
export class HumanReadableDurationPipe implements PipeTransform {
  transform(size: number | bigint | null | undefined): string {
    if (size == null) {
      return '';
    }
    if (typeof size === 'bigint') {
      if (size > Number.MAX_SAFE_INTEGER) {
        console.error(
          `Duration value ${size} is too large to be converted to a number,
              precision might be lost.`,
        );
      }
      size = Number(size);
    }
    return toDurationString(size, 'long');
  }
}
