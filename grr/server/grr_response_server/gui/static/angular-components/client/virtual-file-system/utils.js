'use strict';

goog.module('grrUi.client.virtualFileSystem.utils');
goog.module.declareLegacyNamespace();



/**
 * Adds a trailing forward slash ('/') if it's not already present in the
 * path. In GRR VFS URLs trailing slash signifies directories.
 *
 * @param {string} path
 * @return {string} The given path with a single trailing slash added if needed.
 * @export
 */
exports.ensurePathIsFolder = function(path) {
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
exports.getFolderFromPath = function(path) {
  if (!path) {
    return '';
  }

  var components = path.split('/');
  return components.slice(0, -1).join('/');
};
