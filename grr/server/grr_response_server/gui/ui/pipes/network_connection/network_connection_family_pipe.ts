import {Pipe, PipeTransform} from '@angular/core';

import {NetworkConnectionFamily} from '../../lib/api/api_interfaces';
import {checkExhaustive} from '../../lib/utils';

/**
 * Converts a given NetworkConnectionFamily (IP Version) enum to a more
 * human readable format.
 */
@Pipe({name: 'networkConnectionFamily'})
export class NetworkConnectionFamilyPipe implements PipeTransform {
  transform(family: NetworkConnectionFamily | undefined): string {
    if (family === undefined) {
      return '-';
    }
    switch (family) {
      case NetworkConnectionFamily.INET:
        return 'IPv4';
      case NetworkConnectionFamily.INET6:
        return 'IPv6';
      default:
        checkExhaustive(family);
    }
  }
}
