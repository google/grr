import {HumanReadableFileModePipe} from './human_readable_file_mode_pipe';

describe('Human Readable File Mode Pipe ', () => {
  const pipe = new HumanReadableFileModePipe();

  it('returns - when value is undefined', () => {
    expect(pipe.transform(undefined)).toBe('-');
  });

  it('handles regular files', () => {
    expect(pipe.transform('33188')).toBe('-rw-r--r--');
  });

  it('handles directories', () => {
    expect(pipe.transform('16832')).toBe('drwx------');
  });

  it('handles character devices', () => {
    expect(pipe.transform('8592')).toBe('crw--w----');
  });

  it('handles symbolic links', () => {
    expect(pipe.transform('41325')).toBe('lr-xr-xr-x');
  });

  it('handles block devices', () => {
    expect(pipe.transform('24960')).toBe('brw-------');
  });

  it('handles FIFO pipes', () => {
    expect(pipe.transform('4516')).toBe('prw-r--r--');
  });

  it('handles sockets', () => {
    expect(pipe.transform('50668')).toBe('srwxr-sr--');
  });

  it('handles S_ISUID flag', () => {
    expect(pipe.transform('35300')).toBe('-rwsr--r--');
    expect(pipe.transform('35236')).toBe('-rwSr--r--');
  });

  it('handles S_ISGID flag', () => {
    expect(pipe.transform('36332')).toBe('-rwsr-sr--');
    expect(pipe.transform('36324')).toBe('-rwsr-Sr--');
  });

  it('handles S_ISVTX flag', () => {
    expect(pipe.transform('35812')).toBe('-rwsr--r-T');
    expect(pipe.transform('35813')).toBe('-rwsr--r-t');
  });
});
