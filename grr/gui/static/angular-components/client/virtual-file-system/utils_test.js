'use strict';

goog.require('grrUi.client.virtualFileSystem.utils.ensurePathIsFolder');
goog.require('grrUi.client.virtualFileSystem.utils.getFolderFromPath');

describe('client virtual file system utils', function () {

  describe('ensurePathIsFolder()', function() {
    var ensurePathIsFolder = grrUi.client.virtualFileSystem.utils.ensurePathIsFolder;

    it('does nothing if path ends with "/"', function() {
      expect(ensurePathIsFolder('/')).toBe('/');
      expect(ensurePathIsFolder('a/b/c/')).toBe('a/b/c/');
    });

    it('adds "/" if path does not end with it', function() {
      expect(ensurePathIsFolder('')).toBe('/');
      expect(ensurePathIsFolder('a/b/c')).toBe('a/b/c/');
    });

  });

  describe('getFolderFromPath()', function() {
    var getFolderFromPath = grrUi.client.virtualFileSystem.utils.getFolderFromPath;

    it('does nothing for falsey values', function() {
      expect(getFolderFromPath(null)).toBe('');
      expect(getFolderFromPath(undefined)).toBe('');
      expect(getFolderFromPath('')).toBe('');
    });

    it('strips last component from path with no trailing slash', function() {
      expect(getFolderFromPath('a/b/c')).toBe('a/b');
    });

    it('strips trailing slash only, if there is one', function() {
      expect(getFolderFromPath('a/b/c/')).toBe('a/b/c');
    });
  });

});
