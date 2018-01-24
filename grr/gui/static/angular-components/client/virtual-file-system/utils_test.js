'use strict';

goog.module('grrUi.client.virtualFileSystem.utilsTest');

const utilsEnsurePathIsFolder = goog.require('grrUi.client.virtualFileSystem.utils.ensurePathIsFolder');
const utilsGetFolderFromPath = goog.require('grrUi.client.virtualFileSystem.utils.getFolderFromPath');


describe('client virtual file system utils', () => {
  describe('ensurePathIsFolder()', () => {
    const ensurePathIsFolder = utilsEnsurePathIsFolder;

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
    const getFolderFromPath = utilsGetFolderFromPath;

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
