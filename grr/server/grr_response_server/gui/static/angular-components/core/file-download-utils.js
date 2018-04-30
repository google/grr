'use strict';

goog.module('grrUi.core.fileDownloadUtils');
goog.module.declareLegacyNamespace();



var AFF4_PREFIXES = {
  'OS': "fs/os",  // PathSpec.PathType.OS
  'TSK': "fs/tsk",  // PathSpec.PathType.TSK
  'REGISTRY': "registry",  // PathSpec.PathType.REGISTRY
  'MEMORY': "devices/memory",  // PathSpec.PathType.MEMORY
  'TMPFILE': "temp",  // PathSpec.PathType.TMPFILE
};

/**
 * @param {Object} pathspec
 * @return {Array}
 */
var splitPathspec = function(pathspec) {
  var result = [];

  var cur = pathspec['value'];
  while (angular.isDefined(cur['pathtype'])) {
    result.push(cur);

    if (angular.isDefined(cur['nested_path'])) {
      cur = cur['nested_path']['value'];
    } else {
      break;
    }
  }

  return result;
};

/**
 * Converts a given pathspec to an AFF4 path pointing to a VFS location on a
 * given client.
 *
 * @param {Object} pathspec Typed pathspec value.
 * @param {string} clientId Client id that will be used a base for an AFF4 path.
 * @return {string} AFF4 path built.
 * @export
 */
exports.pathSpecToAff4Path = function(pathspec, clientId) {
  var components = splitPathspec(pathspec);

  var firstComponent = components[0];
  var dev = firstComponent['path']['value'];

  if (angular.isDefined(firstComponent['offset'])) {
    dev += ':' + Math.round(firstComponent['offset']['value'] / 512);
  }

  var result, start;
  if (components.length > 1 && firstComponent['pathtype']['value'] == 'OS' &&
      components[1]['pathtype']['value'] == 'TSK') {
    result = ['aff4:', clientId, AFF4_PREFIXES['TSK'], dev];
    start = 1;
  } else {
    result = ['aff4:', clientId, AFF4_PREFIXES[firstComponent['pathtype']['value']]];
    start = 0;
  }

  for (var i = start; i < components.length; ++i) {
    var p = components[i];
    var component = p['path']['value'];
    if (component.startsWith('/')) {
      component = component.substring(1);
    }

    if (angular.isDefined(p['offset'])) {
      component += ':' + Math.round(p['offset']['value'] / 512);
    }

    if (angular.isDefined(p['stream_name'])) {
      component += ':' + p['stream_name']['value'];
    }

    result.push(component);
  }

  return result.join('/');
};
var pathSpecToAff4Path = exports.pathSpecToAff4Path;


/**
  * List of VFS roots that are accessible through Browse VFS UI.
  *
  * @const {Array<string>}
  */
exports.vfsRoots = ['fs', 'registry', 'temp'];

/**
  * List of VFS roots that contain files that can be downloaded
  * via the API.
  *
  * @const {Array<string>}
  */
exports.downloadableVfsRoots = ['fs', 'temp'];

/**
 * Returns a pathspec of a file that a given value points to.
 *
 * @param {Object} value Typed value.
 * @return {?Object} Pathspec of a file that a given value points to, or null
 *     if there's none.
 * @export
 */
exports.getPathSpecFromValue = function(value) {
  if (!value) {
    return null;
  }

  if (value['type'] == 'ApiFlowResult' || value['type'] == 'ApiHuntResult') {
    value = value['value']['payload'];
  }

  switch (value['type']) {
    case 'StatEntry':
      return value['value']['pathspec'];

    case 'FileFinderResult':
      var st = value['value']['stat_entry'];
      if (angular.isDefined(st) && angular.isDefined(st['value']['pathspec'])) {
        return st['value']['pathspec'];
      }
      return null;
    case 'ArtifactFilesDownloaderResult':
      return exports.getPathSpecFromValue(value['value']['downloaded_file']);

    default:
      return null;
  }
};


/**
 * @param {Object} value
 * @param {string} downloadUrl
 * @param {Object} downloadParams
 */
const makeStatEntryDownloadable_ = function(
    value, downloadUrl, downloadParams) {
  var originalValue = angular.copy(value);
  for (var prop in value) {
    if (value.hasOwnProperty(prop)) {
      delete value[prop];
    }
  }

  angular.extend(value, {
    type: '__DownloadableStatEntry',
    originalValue: originalValue,
    downloadUrl: downloadUrl,
    downloadParams: downloadParams
  });
};


/**
 * @param {Object} value
 * @param {string} downloadUrl
 * @param {Object} downloadParams
 */
const makeFileFinderResultDownloadable_ = function(
    value, downloadUrl, downloadParams) {
  makeStatEntryDownloadable_(
      value['value']['stat_entry'], downloadUrl, downloadParams);
};


/**
 * @param {Object} value
 * @param {string} downloadUrl
 * @param {Object} downloadParams
 */
const makeArtifactFilesDownloaderResultDownloadable_ = function(
    value, downloadUrl, downloadParams) {
  exports.makeValueDownloadable(
      value['value']['downloaded_file'], downloadUrl, downloadParams);
};


/**
 * @param {Object} value
 * @param {string} downloadUrl
 * @param {Object} downloadParams
 * @return {boolean}
 */
exports.makeValueDownloadable = function(value, downloadUrl, downloadParams) {
  if (!value) {
    return false;
  }

  if (value['type'] === 'ApiFlowResult' || value['type'] === 'ApiHuntResult') {
    value = value['value']['payload'];
  }

  switch (value['type']) {
    case 'StatEntry':
      makeStatEntryDownloadable_(value, downloadUrl, downloadParams);
      return true;

    case 'FileFinderResult':
      makeFileFinderResultDownloadable_(value, downloadUrl, downloadParams);
      return true;

    case 'ArtifactFilesDownloaderResult':
      makeArtifactFilesDownloaderResultDownloadable_(
          value, downloadUrl, downloadParams);
      return true;

    default:
      return false;
  }
};
