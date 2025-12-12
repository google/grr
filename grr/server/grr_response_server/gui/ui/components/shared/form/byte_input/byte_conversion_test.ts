import {parseByteString, toByteString, toByteUnit} from './byte_conversion';

describe('toByteString', () => {
  it('correctly renders short format', () => {
    expect(toByteString(2048)).toEqual('2 KiB');
  });

  it('correctly renders long format', () => {
    expect(toByteString(2048, 'long')).toEqual('2 kibibytes');
  });
});

describe('toByteUnit', () => {
  it('correctly renders short format', () => {
    expect(toByteUnit(0)).toEqual([0, 'B']);
    expect(toByteUnit(1)).toEqual([1, 'B']);
    expect(toByteUnit(999)).toEqual([999, 'B']);
    expect(toByteUnit(1023)).toEqual([1023, 'B']);

    expect(toByteUnit(1000)).toEqual([1, 'kB']);
    expect(toByteUnit(1024)).toEqual([1, 'KiB']);
    expect(toByteUnit(999 * 1000)).toEqual([999, 'kB']);
    expect(toByteUnit(1023 * 1024)).toEqual([1023, 'KiB']);

    expect(toByteUnit(1000 * 1000)).toEqual([1, 'MB']);
    expect(toByteUnit(1024 * 1024)).toEqual([1, 'MiB']);
    expect(toByteUnit(999 * 1000 * 1000)).toEqual([999, 'MB']);
    expect(toByteUnit(1023 * 1024 * 1024)).toEqual([1023, 'MiB']);

    expect(toByteUnit(1000 * 1000 * 1000)).toEqual([1, 'GB']);
    expect(toByteUnit(1024 * 1024 * 1024)).toEqual([1, 'GiB']);
    expect(toByteUnit(999 * 1000 * 1000 * 1000)).toEqual([999, 'GB']);
    expect(toByteUnit(1023 * 1024 * 1024 * 1024)).toEqual([1023, 'GiB']);

    expect(toByteUnit(1000 * 1000 * 1000 * 1000)).toEqual([1, 'TB']);
    expect(toByteUnit(1024 * 1024 * 1024 * 1024)).toEqual([1, 'TiB']);
    expect(toByteUnit(999 * 1000 * 1000 * 1000 * 1000)).toEqual([999, 'TB']);
    expect(toByteUnit(1023 * 1024 * 1024 * 1024 * 1024)).toEqual([1023, 'TiB']);

    expect(toByteUnit(1000 * 1000 * 1000 * 1000 * 1000)).toEqual([1, 'PB']);
    expect(toByteUnit(1024 * 1024 * 1024 * 1024 * 1024)).toEqual([1, 'PiB']);
    expect(toByteUnit(999 * 1000 * 1000 * 1000 * 1000 * 1000)).toEqual([
      999,
      'PB',
    ]);
    expect(toByteUnit(1023 * 1024 * 1024 * 1024 * 1024 * 1024)).toEqual([
      1023,
      'PiB',
    ]);

    expect(toByteUnit(1000 * 1000 * 1000 * 1000 * 1000 * 1000)).toEqual([
      1000,
      'PB',
    ]);
    expect(toByteUnit(1024 * 1024 * 1024 * 1024 * 1024 * 1024)).toEqual([
      1024,
      'PiB',
    ]);
  });

  it('correctly renders long format', () => {
    expect(toByteUnit(0, 'long')).toEqual([0, 'bytes']);
    expect(toByteUnit(1, 'long')).toEqual([1, 'byte']);
    expect(toByteUnit(999, 'long')).toEqual([999, 'bytes']);
    expect(toByteUnit(1023, 'long')).toEqual([1023, 'bytes']);

    expect(toByteUnit(1000, 'long')).toEqual([1, 'kilobyte']);
    expect(toByteUnit(1024, 'long')).toEqual([1, 'kibibyte']);
    expect(toByteUnit(999 * 1000, 'long')).toEqual([999, 'kilobytes']);
    expect(toByteUnit(1023 * 1024, 'long')).toEqual([1023, 'kibibytes']);

    expect(toByteUnit(1000 * 1000, 'long')).toEqual([1, 'megabyte']);
    expect(toByteUnit(1024 * 1024, 'long')).toEqual([1, 'mebibyte']);
    expect(toByteUnit(999 * 1000 * 1000, 'long')).toEqual([999, 'megabytes']);
    expect(toByteUnit(1023 * 1024 * 1024, 'long')).toEqual([1023, 'mebibytes']);

    expect(toByteUnit(1000 * 1000 * 1000, 'long')).toEqual([1, 'gigabyte']);
    expect(toByteUnit(1024 * 1024 * 1024, 'long')).toEqual([1, 'gibibyte']);
    expect(toByteUnit(999 * 1000 * 1000 * 1000, 'long')).toEqual([
      999,
      'gigabytes',
    ]);
    expect(toByteUnit(1023 * 1024 * 1024 * 1024, 'long')).toEqual([
      1023,
      'gibibytes',
    ]);

    expect(toByteUnit(1000 * 1000 * 1000 * 1000, 'long')).toEqual([
      1,
      'terabyte',
    ]);
    expect(toByteUnit(1024 * 1024 * 1024 * 1024, 'long')).toEqual([
      1,
      'tebibyte',
    ]);
    expect(toByteUnit(999 * 1000 * 1000 * 1000 * 1000, 'long')).toEqual([
      999,
      'terabytes',
    ]);
    expect(toByteUnit(1023 * 1024 * 1024 * 1024 * 1024, 'long')).toEqual([
      1023,
      'tebibytes',
    ]);

    expect(toByteUnit(1000 * 1000 * 1000 * 1000 * 1000, 'long')).toEqual([
      1,
      'petabyte',
    ]);
    expect(toByteUnit(1024 * 1024 * 1024 * 1024 * 1024, 'long')).toEqual([
      1,
      'pebibyte',
    ]);
    expect(toByteUnit(999 * 1000 * 1000 * 1000 * 1000 * 1000, 'long')).toEqual([
      999,
      'petabytes',
    ]);
    expect(toByteUnit(1023 * 1024 * 1024 * 1024 * 1024 * 1024, 'long')).toEqual(
      [1023, 'pebibytes'],
    );

    expect(toByteUnit(1000 * 1000 * 1000 * 1000 * 1000 * 1000, 'long')).toEqual(
      [1000, 'petabytes'],
    );
    expect(toByteUnit(1024 * 1024 * 1024 * 1024 * 1024 * 1024, 'long')).toEqual(
      [1024, 'pebibytes'],
    );
  });
});

describe('parseByteString', () => {
  it('correctly parses strings without unit', () => {
    expect(parseByteString('0')).toEqual(0);
    expect(parseByteString('1')).toEqual(1);
    expect(parseByteString('1024')).toEqual(1024);
    expect(parseByteString('1024000')).toEqual(1024000);
  });

  it('ignores whitespace, byte suffix, and casing', () => {
    expect(parseByteString('  10  KIB   ')).toEqual(10240);
    expect(parseByteString('10Ki')).toEqual(10240);
    expect(parseByteString('10K')).toEqual(10000);
    expect(parseByteString('10kib')).toEqual(10240);
    expect(parseByteString('10kB')).toEqual(10000);
    expect(parseByteString('10Kb')).toEqual(10000);
  });

  it('correctly parses strings with base-10 unit', () => {
    expect(parseByteString('0 K')).toEqual(0);
    expect(parseByteString('1 K')).toEqual(1000);
    expect(parseByteString('999 K')).toEqual(999000);
    expect(parseByteString('1000 K')).toEqual(1000000);
    expect(parseByteString('1 M')).toEqual(1000000);
    expect(parseByteString('999 M')).toEqual(999000000);
    expect(parseByteString('1 G')).toEqual(1000000000);
    expect(parseByteString('999 G')).toEqual(999000000000);
    expect(parseByteString('1 T')).toEqual(1000000000000);
    expect(parseByteString('999 T')).toEqual(999000000000000);
    expect(parseByteString('1 P')).toEqual(1000000000000000);
    expect(parseByteString('9 P')).toEqual(9000000000000000);
    // JavaScript does not support integers larger than ~ 9P. These will be
    // converted to floating point numbers and lose their precision.
  });

  it('correctly parses strings with base-2 unit', () => {
    expect(parseByteString('0 Ki')).toEqual(0);
    expect(parseByteString('1 Ki')).toEqual(1024);
    expect(parseByteString('1000 Ki')).toEqual(1024000);
    expect(parseByteString('1 Mi')).toEqual(1024 * 1024);
    expect(parseByteString('999 Mi')).toEqual(999 * 1024 * 1024);
    expect(parseByteString('1 Gi')).toEqual(1024 * 1024 * 1024);
    expect(parseByteString('999 Gi')).toEqual(999 * 1024 * 1024 * 1024);
    expect(parseByteString('1 Ti')).toEqual(1024 * 1024 * 1024 * 1024);
    expect(parseByteString('999 Ti')).toEqual(999 * 1024 * 1024 * 1024 * 1024);
    expect(parseByteString('1 Pi')).toEqual(1024 * 1024 * 1024 * 1024 * 1024);
    expect(parseByteString('7 Pi')).toEqual(
      7 * 1024 * 1024 * 1024 * 1024 * 1024,
    );
    // JavaScript does not support integers larger than ~ 7Pi. These will be
    // converted to floating point numbers and lose their precision.
  });
});
