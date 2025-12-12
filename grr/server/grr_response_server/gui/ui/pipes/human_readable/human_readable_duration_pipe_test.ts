import {HumanReadableDurationPipe} from './human_readable_duration_pipe';

describe('Human Readable Duration Pipe', () => {
  const pipe = new HumanReadableDurationPipe();

  it('is blank when no size provided', () => {
    expect(pipe.transform(null)).toEqual('');
  });

  it('shows the provided number size in a human readable format', () => {
    expect(pipe.transform(0)).toEqual('0 seconds');
    expect(pipe.transform(2)).toEqual('2 seconds');

    expect(pipe.transform(60)).toEqual('1 minute');
    expect(pipe.transform(120)).toEqual('2 minutes');

    expect(pipe.transform(60 * 60)).toEqual('1 hour');
    expect(pipe.transform(60 * 60 * 23)).toEqual('23 hours');

    expect(pipe.transform(60 * 60 * 24)).toEqual('1 day');
    expect(pipe.transform(60 * 60 * 24 * 6)).toEqual('6 days');

    expect(pipe.transform(60 * 60 * 24 * 7)).toEqual('1 week');
    expect(pipe.transform(60 * 60 * 24 * 7 * 2)).toEqual('2 weeks');

    expect(pipe.transform(60 * 60 * 24 * 356)).toEqual('356 days');
  });

  it('shows the provided bigint size in a human readable format', () => {
    expect(pipe.transform(BigInt(0))).toEqual('0 seconds');
    expect(pipe.transform(BigInt(2))).toEqual('2 seconds');
  });
});
