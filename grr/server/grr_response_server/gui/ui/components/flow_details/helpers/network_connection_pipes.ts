import {Pipe, PipeTransform} from '@angular/core';

import {NetworkConnectionFamily, NetworkConnectionType} from '../../../lib/api/api_interfaces';

const NETWORK_CONNECTION_FAMILY_MAP:
    ReadonlyMap<NetworkConnectionFamily, string> = new Map([
      [NetworkConnectionFamily.INET, 'IPv4'],
      [NetworkConnectionFamily.INET6, 'IPv6'],
      [NetworkConnectionFamily.INET6_WIN, 'IPv6'],
      [NetworkConnectionFamily.INET6_OSX, 'IPv6'],
    ]);

const NETWORK_CONNECTION_TYPE_MAP: ReadonlyMap<NetworkConnectionType, string> =
    new Map([
      [NetworkConnectionType.UNKNOWN_SOCKET, '?'],
      [NetworkConnectionType.SOCK_STREAM, 'TCP'],
      [NetworkConnectionType.SOCK_DGRAM, 'UDP'],
    ]);

/**
 * Converts a given NetworkConnectionFamily (IP Version) enum to a more
 * human readable format.
 */
@Pipe({name: 'networkConnectionFamily'})
export class NetworkConnectionFamilyPipe implements PipeTransform {
  transform(family: NetworkConnectionFamily|undefined): string {
    if (family === undefined) {
      return '-';
    }
    return NETWORK_CONNECTION_FAMILY_MAP.get(family) ?? '-';
  }
}

/**
 * Converts a given NetworkConnectionType (IP Version) enum to a more
 * human readable format.
 */
@Pipe({name: 'networkConnectionType'})
export class NetworkConnectionTypePipe implements PipeTransform {
  transform(type: NetworkConnectionType|undefined): string {
    if (type === undefined) {
      return '-';
    }
    return NETWORK_CONNECTION_TYPE_MAP.get(type) ?? '-';
  }
}
