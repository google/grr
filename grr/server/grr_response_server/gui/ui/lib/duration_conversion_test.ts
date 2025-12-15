import {
  parseDurationString,
  toDurationString,
  toDurationUnit,
} from './duration_conversion';

describe('toDurationString', () => {
  it('correctly renders short format', () => {
    expect(toDurationString(3600)).toEqual('1 h');

    expect(toDurationString(0)).toEqual('0 s');

    expect(toDurationString(0.1111111)).toEqual('0 s');
    expect(toDurationString(0.7999999821186066)).toEqual('1 s');
    expect(toDurationString(1.002)).toEqual('1 s');
    expect(toDurationString(1.7999999821186066)).toEqual('2 s');
  });

  it('correctly renders long format', () => {
    expect(toDurationString(3600, 'long')).toEqual('1 hour');
  });
});

describe('toDurationUnit', () => {
  it('correctly renders short format', () => {
    expect(toDurationUnit(0)).toEqual([0, 's']);
    expect(toDurationUnit(1)).toEqual([1, 's']);
    expect(toDurationUnit(50)).toEqual([50, 's']);

    expect(toDurationUnit(60)).toEqual([1, 'm']);
    expect(toDurationUnit(60 * 5)).toEqual([5, 'm']);

    expect(toDurationUnit(60 * 60)).toEqual([1, 'h']);
    expect(toDurationUnit(5 * 60 * 60)).toEqual([5, 'h']);

    expect(toDurationUnit(24 * 60 * 60)).toEqual([1, 'd']);
    expect(toDurationUnit(48 * 60 * 60)).toEqual([2, 'd']);

    expect(toDurationUnit(7 * 24 * 60 * 60)).toEqual([1, 'w']);
  });

  it('correctly renders long format', () => {
    expect(toDurationUnit(0, 'long')).toEqual([0, 'seconds']);
    expect(toDurationUnit(1, 'long')).toEqual([1, 'second']);
    expect(toDurationUnit(50, 'long')).toEqual([50, 'seconds']);

    expect(toDurationUnit(60, 'long')).toEqual([1, 'minute']);
    expect(toDurationUnit(60 * 5, 'long')).toEqual([5, 'minutes']);

    expect(toDurationUnit(60 * 60, 'long')).toEqual([1, 'hour']);
    expect(toDurationUnit(5 * 60 * 60, 'long')).toEqual([5, 'hours']);

    expect(toDurationUnit(24 * 60 * 60, 'long')).toEqual([1, 'day']);
    expect(toDurationUnit(48 * 60 * 60, 'long')).toEqual([2, 'days']);

    expect(toDurationUnit(7 * 24 * 60 * 60, 'long')).toEqual([1, 'week']);
  });
});

describe('parseDurationString', () => {
  it('correctly parses strings without unit', () => {
    expect(parseDurationString('0')).toEqual(0);
    expect(parseDurationString('1')).toEqual(1);
    expect(parseDurationString('50')).toEqual(50);
  });

  it('ignores whitespace, duration suffix, and casing', () => {
    expect(parseDurationString('  10  S   ')).toEqual(10);
    expect(parseDurationString('10s')).toEqual(10);
    expect(parseDurationString('10m')).toEqual(10 * 60);
    expect(parseDurationString('3w')).toEqual(3 * 7 * 24 * 60 * 60);
    expect(parseDurationString('5  d')).toEqual(5 * 24 * 60 * 60);
  });
});
