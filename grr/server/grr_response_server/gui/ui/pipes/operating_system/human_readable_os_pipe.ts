import {Pipe, PipeTransform} from '@angular/core';
import {OperatingSystem} from '../../lib/models/flow';

/**
 * Pipe which converts an OperatingSystem to a human readable string.
 */
@Pipe({name: 'humanReadableOs'})
export class HumanReadableOsPipe implements PipeTransform {
  transform(os: OperatingSystem): string {
    return String(os);
  }
}
