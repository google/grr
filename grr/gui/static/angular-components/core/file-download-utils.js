'use strict';

goog.provide('grrUi.core.fileDownloadUtils.getFileUrnFromValue');
goog.provide('grrUi.core.fileDownloadUtils.makeValueDownloadable');


goog.scope(function() {


var fileDownloadUtils = grrUi.core.fileDownloadUtils;


/**
 * Returns AFF4 path of a file that a given value points to.
 *
 * @param {Object} value Typed value.
 * @return {?string} Urn of an AFF4 file that a given value points to, or null
 *     if there's none.
 * @export
 */
fileDownloadUtils.getFileUrnFromValue = function(value) {
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
    return value['value']['stat_entry']['value']['aff4path']['value'];

    case 'ArtifactFilesDownloaderResult':
    return fileDownloadUtils.getFileUrnFromValue(
        value['value']['downloaded_file']);

    default:
    return null;
  }
};


fileDownloadUtils.makeStatEntryDownloadable_ = function(
    value, downloadUrl, downloadParams) {
  value['value']['aff4path'] = {
    type: '__DownloadableUrn',
    originalValue: value['value']['aff4path'],
    downloadUrl: downloadUrl,
    downloadParams: downloadParams
  };
};


fileDownloadUtils.makeFileFinderResultDownloadable_ = function(
    value, downloadUrl, downloadParams) {
  fileDownloadUtils.makeStatEntryDownloadable_(
      value['value']['stat_entry'], downloadUrl, downloadParams);
};


fileDownloadUtils.makeArtifactFilesDownloaderResultDownloadable_ = function(
    value, downloadUrl, downloadParams) {
  fileDownloadUtils.makeValueDownloadable(
      value['value']['downloaded_file'], downloadUrl, downloadParams);
};


fileDownloadUtils.makeValueDownloadable = function(
    value, downloadUrl, downloadParams) {
  if (!value) {
    return false;
  }

  if (value['type'] === 'ApiFlowResult' || value['type'] === 'ApiHuntResult') {
    value = value['value']['payload'];
  }

  switch (value['type']) {
    case 'StatEntry':
    fileDownloadUtils.makeStatEntryDownloadable_(
        value, downloadUrl, downloadParams);
    return true;

    case 'FileFinderResult':
    fileDownloadUtils.makeFileFinderResultDownloadable_(
        value, downloadUrl, downloadParams);
    return true;

    case 'ArtifactFilesDownloaderResult':
    fileDownloadUtils.makeArtifactFilesDownloaderResultDownloadable_(
        value, downloadUrl, downloadParams);
    return true;

    default:
    return false;
  }
};


});  // goog.scope
