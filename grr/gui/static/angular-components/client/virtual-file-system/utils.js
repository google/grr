'use strict';

goog.provide('grrUi.client.virtualFileSystem.utils.ensurePathIsFolder');
goog.provide('grrUi.client.virtualFileSystem.utils.getFolderFromPath');


goog.scope(function() {


/**
 * Adds a trailing forward slash ('/') if it's not already present in the
 * path. In GRR VFS URLs trailing slash signifies directories.
 *
 * @param {string} path
 * @return {string} The given path with a single trailing slash added if needed.
 * @export
 */
grrUi.client.virtualFileSystem.utils.ensurePathIsFolder = function(path) {
  if (path.endsWith('/')) {
    return path;
  } else {
    return path + '/';
  }
};


/**
 * Strips last path component from the path. If the path ends with
 * a trailing slash, just the slash will be stripped.
 *
 * @param {?string} path
 * @return {string} The given path with a trailing slash stripped.
 * @export
 */
grrUi.client.virtualFileSystem.utils.getFolderFromPath = function(path) {
  if (!path) {
    return '';
  }

  var components = path.split('/');
  return components.slice(0, -1).join('/');
};


});
