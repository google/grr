import {NetworkConnectionFamily} from '../../lib/api/api_interfaces';
import {NetworkConnectionFamilyPipe} from './network_connection_family_pipe';

describe('Network Connection Family Pipe', () => {
  const pipe = new NetworkConnectionFamilyPipe();

  it('translates undefined', () => {
    expect(pipe.transform(undefined)).toBe('-');
  });

  it('translates INET', () => {
    expect(pipe.transform(NetworkConnectionFamily.INET)).toBe('IPv4');
  });

  it('translates INET6', () => {
    expect(pipe.transform(NetworkConnectionFamily.INET6)).toBe('IPv6');
  });
});
