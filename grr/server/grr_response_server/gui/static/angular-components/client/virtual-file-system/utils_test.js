'use strict';

goog.module('grrUi.client.virtualFileSystem.utilsTest');

const {ensurePathIsFolder, getFolderFromPath} = goog.require('grrUi.client.virtualFileSystem.utils');


describe('client virtual file system utils', () => {
  describe('ensurePathIsFolder()', () => {

    it('does nothing if path ends with "/"', () => {
      expect(ensurePathIsFolder('/')).toBe('/');
      expect(ensurePathIsFolder('a/b/c/')).toBe('a/b/c/');
    });

    it('adds "/" if path does not end with it', () => {
      expect(ensurePathIsFolder('')).toBe('/');
      expect(ensurePathIsFolder('a/b/c')).toBe('a/b/c/');
    });
  });

  describe('getFolderFromPath()', () => {

    it('does nothing for falsey values', () => {
      expect(getFolderFromPath(null)).toBe('');
      expect(getFolderFromPath(undefined)).toBe('');
      expect(getFolderFromPath('')).toBe('');
    });

    it('strips last component from path with no trailing slash', () => {
      expect(getFolderFromPath('a/b/c')).toBe('a/b');
    });

    it('strips trailing slash only, if there is one', () => {
      expect(getFolderFromPath('a/b/c/')).toBe('a/b/c');
    });
  });
});


exports = {};
