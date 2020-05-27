import {initTestEnvironment} from '../../testing';

import {createDate, createOptionalDate, createOptionalDateSeconds} from './primitive';


initTestEnvironment();

describe('createDate', () => {
  it('throws for empty string', () => {
    expect(() => createDate('')).toThrowError(/empty/);
  });
  it('throws for invalid string', () => {
    expect(() => createDate('123abc')).toThrowError(/invalid/);
  });
  it('handles unix epoch correctly', () => {
    expect(createDate('0')).toEqual(new Date(0));
  });
  it('handles unixtimes correctly', () => {
    expect(createDate('1579167695123000')).toEqual(new Date(1579167695123));
  });
  it('truncates microseconds', () => {
    expect(createDate('1579167695123999')).toEqual(new Date(1579167695123));
  });
  it('handles future timestamps', () => {
    const y2100 = 130 * 365 * 86400 * 1000;
    expect(createDate((y2100 * 1000).toString())).toEqual(new Date(y2100));
  });
});

describe('createOptionalDate', () => {
  it('returns undefined for undefined', () => {
    expect(createOptionalDate(undefined)).toBeUndefined();
  });
  it('returns undefined for empty string', () => {
    expect(createOptionalDate('')).toBeUndefined();
  });
  it('throws for invalid string', () => {
    expect(() => createOptionalDate('123abc')).toThrowError(/invalid/);
  });
  it('handles unix epoch correctly', () => {
    expect(createOptionalDate('0')).toEqual(new Date(0));
  });
  it('handles unixtimes correctly', () => {
    expect(createOptionalDate('1579167695123000'))
        .toEqual(new Date(1579167695123));
  });
  it('truncates microseconds', () => {
    expect(createOptionalDate('1579167695123999'))
        .toEqual(new Date(1579167695123));
  });
  it('handles future timestamps', () => {
    const y2100 = 130 * 365 * 86400 * 1000;
    expect(createOptionalDate((y2100 * 1000).toString()))
        .toEqual(new Date(y2100));
  });
});

describe('createOptionalDateSeconds', () => {
  it('returns undefined for undefined', () => {
    expect(createOptionalDateSeconds(undefined)).toBeUndefined();
  });
  it('returns undefined for empty string', () => {
    expect(createOptionalDateSeconds('')).toBeUndefined();
  });
  it('throws for invalid string', () => {
    expect(() => createOptionalDateSeconds('123abc')).toThrowError(/invalid/);
  });
  it('handles unix epoch correctly', () => {
    expect(createOptionalDateSeconds('0')).toEqual(new Date(0));
  });
  it('handles unixtimes correctly', () => {
    expect(createOptionalDateSeconds('1579167695'))
        .toEqual(new Date(1579167695000));
  });
});
