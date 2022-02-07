import {initTestEnvironment} from '../../testing';

import {isSubDirectory, pathDepth, scanPath} from './vfs';

initTestEnvironment();

describe('scanPath', () => {
  it('parses the root path "/"', () => {
    expect(scanPath('/')).toEqual(['/']);
  });

  it('parses a one-level path', () => {
    expect(scanPath('/foo')).toEqual(['/', '/foo']);
    expect(scanPath('/foo/')).toEqual(['/', '/foo']);
  });

  it('parses a nested path', () => {
    expect(scanPath('/foo/bar')).toEqual(['/', '/foo', '/foo/bar']);
    expect(scanPath('/foo/bar/')).toEqual(['/', '/foo', '/foo/bar']);
  });
});

describe('isSubDirectory', () => {
  it('returns true for real sub directories', () => {
    expect(isSubDirectory('/foo', '/')).toBe(true);
    expect(isSubDirectory('/foo/bar', '/foo')).toBe(true);
    expect(isSubDirectory('/foo/foo', '/foo')).toBe(true);
    expect(isSubDirectory('/foo/foo/', '/foo')).toBe(true);
    expect(isSubDirectory('/foo/foo/', '/foo/')).toBe(true);
    expect(isSubDirectory('/foo/foo', '/foo/')).toBe(true);
  });

  it('returns false for the same directory', () => {
    expect(isSubDirectory('/', '/')).toBe(false);
    expect(isSubDirectory('/bar', '/bar')).toBe(false);
    expect(isSubDirectory('/bar/', '/bar')).toBe(false);
    expect(isSubDirectory('/bar', '/bar/')).toBe(false);
    expect(isSubDirectory('/bar/', '/bar/')).toBe(false);
    expect(isSubDirectory('/bar/baz', '/bar/baz')).toBe(false);
  });

  it('returns false for parent directories', () => {
    expect(isSubDirectory('/', '/foo')).toBe(false);
    expect(isSubDirectory('/foo', '/foo/bar')).toBe(false);
  });

  it('returns false for sibling directories', () => {
    expect(isSubDirectory('/foo', '/bar')).toBe(false);
    expect(isSubDirectory('/foooo', '/foo')).toBe(false);
    expect(isSubDirectory('/foo', '/fooo')).toBe(false);
  });
});

describe('pathDepth', () => {
  it('returns 1 for root', () => {
    expect(pathDepth('/')).toBe(1);
  });

  it('returns the depth', () => {
    expect(pathDepth('/foo')).toBe(2);
    expect(pathDepth('/foo/bar')).toBe(3);
  });

  it('ignores a trailing slash', () => {
    expect(pathDepth('/foo/')).toBe(2);
    expect(pathDepth('/foo/bar/')).toBe(3);
  });
});
