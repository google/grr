import {HumanReadableByteSizePipe} from './human_readable_byte_size_pipe';

describe('Human Readable Byte Size Pipe', () => {
  const pipe = new HumanReadableByteSizePipe();

  it('is blank when no size provided', () => {
    expect(pipe.transform(null)).toEqual('');
  });

  it('is blank when the provided size is undefined', () => {
    expect(pipe.transform(undefined)).toEqual('');
  });

  it('is blank when the provided size is smaller than 0', () => {
    expect(pipe.transform(-1024)).toEqual('');
  });

  it('shows the provided size in a human readable format', () => {
    expect(pipe.transform(0)).toEqual('0 B');
    expect(pipe.transform(1 / 3)).toEqual('0 B');
    expect(pipe.transform(1023)).toEqual('1023 B');
    expect(pipe.transform(1023.9)).toEqual('1023 B');

    expect(pipe.transform(1024)).toEqual('1.00 KiB');
    expect(pipe.transform(1034)).toEqual('1.00 KiB');
    expect(pipe.transform(1035)).toEqual('1.01 KiB');
    expect(pipe.transform(Math.pow(1024, 2) - 1)).toEqual('1023.99 KiB');

    expect(pipe.transform(Math.pow(1024, 2))).toEqual('1.00 MiB');
    expect(pipe.transform(Math.pow(1024, 3) - 1)).toEqual('1023.99 MiB');

    expect(pipe.transform(Math.pow(1024, 3))).toEqual('1.00 GiB');
    expect(pipe.transform(Math.pow(1024, 4) - 1)).toEqual('1023.99 GiB');

    expect(pipe.transform(Math.pow(1024, 4))).toEqual('1.00 TiB');
    expect(pipe.transform(Math.pow(1024, 5) - 1)).toEqual('1023.99 TiB');

    expect(pipe.transform(Math.pow(1024, 5))).toEqual('1.00 PiB');
    expect(pipe.transform(Math.pow(1024, 6) * 324)).toEqual('331776.00 PiB');
  });
});
