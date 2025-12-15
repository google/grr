import {NetworkConnectionType} from '../../lib/api/api_interfaces';
import {NetworkConnectionTypePipe} from './network_connection_type_pipe';

describe('Network Connection Type Pipe', () => {
  const pipe = new NetworkConnectionTypePipe();

  it('translates undefined', () => {
    expect(pipe.transform(undefined)).toBe('-');
  });

  it('translates UNKNOWN_SOCKET', () => {
    expect(pipe.transform(NetworkConnectionType.UNKNOWN_SOCKET)).toBe('?');
  });

  it('translates SOCK_STREAM', () => {
    expect(pipe.transform(NetworkConnectionType.SOCK_STREAM)).toBe('TCP');
  });

  it('translates SOCK_DGRAM', () => {
    expect(pipe.transform(NetworkConnectionType.SOCK_DGRAM)).toBe('UDP');
  });
});
