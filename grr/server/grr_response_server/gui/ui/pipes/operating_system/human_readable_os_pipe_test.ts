import {OperatingSystem} from '../../lib/models/flow';
import {HumanReadableOsPipe} from './human_readable_os_pipe';

describe('Set to Array Pipe', () => {
  const pipe = new HumanReadableOsPipe();

  it('returns the expected string for every os', () => {
    expect(pipe.transform(OperatingSystem.LINUX)).toEqual('Linux');
    expect(pipe.transform(OperatingSystem.WINDOWS)).toEqual('Windows');
    expect(pipe.transform(OperatingSystem.DARWIN)).toEqual('Darwin');
  });
});
