import {Pipe, PipeTransform} from '@angular/core';

import {NetworkConnectionType} from '../../lib/api/api_interfaces';
import {checkExhaustive} from '../../lib/utils';

/**
 * Converts a given NetworkConnectionType (IP Version) enum to a more
 * human readable format.
 */
@Pipe({name: 'networkConnectionType'})
export class NetworkConnectionTypePipe implements PipeTransform {
  transform(type: NetworkConnectionType | undefined): string {
    if (type === undefined) {
      return '-';
    }
    switch (type) {
      case NetworkConnectionType.UNKNOWN_SOCKET:
        return '?';
      case NetworkConnectionType.SOCK_STREAM:
        return 'TCP';
      case NetworkConnectionType.SOCK_DGRAM:
        return 'UDP';
      default:
        checkExhaustive(type);
    }
  }
}
