'use strict';

goog.provide('grrUi.core.fileDownloadUtils.downloadableVfsRoots');
goog.provide('grrUi.core.fileDownloadUtils.getFileUrnFromValue');
goog.provide('grrUi.core.fileDownloadUtils.makeValueDownloadable');
goog.provide('grrUi.core.fileDownloadUtils.vfsRoots');


goog.scope(function() {


/**
  * List of VFS roots that are accessible through Browse VFS UI.
  *
  * @const {Array<string>}
  */
grrUi.core.fileDownloadUtils.vfsRoots = ['fs', 'registry', 'temp'];

/**
  * List of VFS roots that contain files that can be downloaded
  * via the API.
  *
  * @const {Array<string>}
  */
grrUi.core.fileDownloadUtils.downloadableVfsRoots = ['fs', 'temp'];

/**
 * Returns AFF4 path of a file that a given value points to.
 *
 * @param {Object} value Typed value.
 * @return {?string} Urn of an AFF4 file that a given value points to, or null
 *     if there's none.
 * @export
 */
grrUi.core.fileDownloadUtils.getFileUrnFromValue = function(value) {
  if (!value) {
    return null;
  }

  if (value['type'] == 'ApiFlowResult' || value['type'] == 'ApiHuntResult') {
    value = value['value']['payload'];
  }

  switch (value['type']) {
    case 'StatEntry':
    return value['value']['aff4path']['value'];

    case 'FileFinderResult':
    if (angular.isDefined(value['value']['stat_entry']['value']['aff4path'])) {
      return value['value']['stat_entry']['value']['aff4path']['value'];
    }
    return null;
    case 'ArtifactFilesDownloaderResult':
    return grrUi.core.fileDownloadUtils.getFileUrnFromValue(
        value['value']['downloaded_file']);

    default:
    return null;
  }
};


grrUi.core.fileDownloadUtils.makeStatEntryDownloadable_ = function(
    value, downloadUrl, downloadParams) {
  value['value']['aff4path'] = {
    type: '__DownloadableUrn',
    originalValue: value['value']['aff4path'],
    downloadUrl: downloadUrl,
    downloadParams: downloadParams
  };
};


grrUi.core.fileDownloadUtils.makeFileFinderResultDownloadable_ = function(
    value, downloadUrl, downloadParams) {
  grrUi.core.fileDownloadUtils.makeStatEntryDownloadable_(
      value['value']['stat_entry'], downloadUrl, downloadParams);
};


grrUi.core.fileDownloadUtils.makeArtifactFilesDownloaderResultDownloadable_ = function(
    value, downloadUrl, downloadParams) {
  grrUi.core.fileDownloadUtils.makeValueDownloadable(
      value['value']['downloaded_file'], downloadUrl, downloadParams);
};


grrUi.core.fileDownloadUtils.makeValueDownloadable = function(
    value, downloadUrl, downloadParams) {
  if (!value) {
    return false;
  }

  if (value['type'] === 'ApiFlowResult' || value['type'] === 'ApiHuntResult') {
    value = value['value']['payload'];
  }

  switch (value['type']) {
    case 'StatEntry':
    grrUi.core.fileDownloadUtils.makeStatEntryDownloadable_(
        value, downloadUrl, downloadParams);
    return true;

    case 'FileFinderResult':
    grrUi.core.fileDownloadUtils.makeFileFinderResultDownloadable_(
        value, downloadUrl, downloadParams);
    return true;

    case 'ArtifactFilesDownloaderResult':
    grrUi.core.fileDownloadUtils.makeArtifactFilesDownloaderResultDownloadable_(
        value, downloadUrl, downloadParams);
    return true;

    default:
    return false;
  }
};


});  // goog.scope
