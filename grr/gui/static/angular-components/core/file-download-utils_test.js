'use strict';

goog.require('grrUi.core.fileDownloadUtils.getFileUrnFromValue');
goog.require('grrUi.core.fileDownloadUtils.makeValueDownloadable');

describe('fileDownloadUtils', function() {
  var statEntry, fileFinderResult, artifactFilesDownloaderResult, rdfstring;

  beforeEach(function() {
    statEntry = {
      value: {
        aff4path: {
          value: 'aff4:/foo/bar',
          type: 'RDFURN'
        }
      },
      type: 'StatEntry'
    };

    fileFinderResult = {
      value: {
        stat_entry: angular.copy(statEntry)
      },
      type: 'FileFinderResult'
    };

    artifactFilesDownloaderResult = {
      value: {
        downloaded_file: angular.copy(statEntry)
      },
      type: 'ArtifactFilesDownloaderResult'
    };

    rdfstring = {
      value: 'blah',
      type: 'RDFString'
    };
  });

  describe('getFileUrnFromValue', function() {
    var getFileUrnFromValue = grrUi.core.fileDownloadUtils.getFileUrnFromValue;

    it('returns null if argument is null or undefined', function() {
      expect(getFileUrnFromValue(null)).toBe(null);
      expect(getFileUrnFromValue(undefined)).toBe(null);
    });

    it('extracts urn from StatEntry', function() {
      expect(getFileUrnFromValue(statEntry)).toBe('aff4:/foo/bar');
    });

    it('extracts urn from FileFinderResult', function() {
      expect(getFileUrnFromValue(fileFinderResult)).toBe('aff4:/foo/bar');
    });

    it('extracts urn from ArtifactFilesDownloaderResult', function() {
      expect(getFileUrnFromValue(artifactFilesDownloaderResult)).toBe(
          'aff4:/foo/bar');
    });

    it('extracts urn recursively from ApiFlowResult', function() {
      var apiFlowResult = {
        value: {
          payload: angular.copy(statEntry)
        },
        type: 'ApiFlowResult'
      };
      expect(getFileUrnFromValue(apiFlowResult)).toBe('aff4:/foo/bar');

      apiFlowResult = {
        value: {
          payload: angular.copy(fileFinderResult)
        },
        type: 'ApiFlowResult'
      };
      expect(getFileUrnFromValue(apiFlowResult)).toBe('aff4:/foo/bar');

      apiFlowResult = {
        value: {
          payload: angular.copy(artifactFilesDownloaderResult)
        },
        type: 'ApiFlowResult'
      };
      expect(getFileUrnFromValue(apiFlowResult)).toBe('aff4:/foo/bar');
    });

    it('extracts urn recursively from ApiHuntResult', function() {
      var apiHuntResult = {
        value: {
          payload: angular.copy(statEntry)
        },
        type: 'ApiHuntResult'
      };
      expect(getFileUrnFromValue(apiHuntResult)).toBe('aff4:/foo/bar');

      apiHuntResult = {
        value: {
          payload: angular.copy(fileFinderResult)
        },
        type: 'ApiHuntResult'
      };
      expect(getFileUrnFromValue(apiHuntResult)).toBe('aff4:/foo/bar');

      apiHuntResult = {
        value: {
          payload: angular.copy(artifactFilesDownloaderResult)
        },
        type: 'ApiHuntResult'
      };
      expect(getFileUrnFromValue(apiHuntResult)).toBe('aff4:/foo/bar');
    });

    it('returns null for other aff4 types', function() {
      expect(getFileUrnFromValue(rdfstring)).toBe(null);
    });

    it('returns null for other types wrapped in ApiFlowResult', function() {
      var apiFlowResult = {
        value: {
          payload: angular.copy(rdfstring)
        },
        type: 'ApiFlowResult'
      };
      expect(getFileUrnFromValue(apiFlowResult)).toBe(null);
    });

    it('returns null for other types wrapped in ApiHuntResult', function() {
      var apiHuntResult = {
        value: {
          payload: angular.copy(rdfstring)
        },
        type: 'ApiHuntResult'
      };
      expect(getFileUrnFromValue(apiHuntResult)).toBe(null);
    });
  });


  describe('makeValueDownloadable', function() {
    var makeValueDownloadable =
        grrUi.core.fileDownloadUtils.makeValueDownloadable;

    var downloadUrl = 'download/foo/bar';
    var downloadParams = {
      foo: 'bar',
      blah: 'blah'
    };

    it('does nothing if argument is null or undefned', function() {
      expect(makeValueDownloadable(null, downloadUrl, downloadParams))
          .toBe(false);
      expect(makeValueDownloadable(undefined, downloadUrl, downloadParams))
          .toBe(false);
    });

    it('replaces aff4path in StatEntry', function() {
      var originalStatEntry = angular.copy(statEntry);

      expect(makeValueDownloadable(statEntry, downloadUrl, downloadParams))
          .toBe(true);
      expect(statEntry.value.aff4path).toEqual({
        downloadUrl: downloadUrl,
        downloadParams: downloadParams,
        originalValue: originalStatEntry.value.aff4path,
        type: "__DownloadableUrn"
      });
    });

    it('replaces aff4path in FileFinderResult', function() {
      var originalFileFinderResult = angular.copy(fileFinderResult);

      expect(makeValueDownloadable(
          fileFinderResult, downloadUrl, downloadParams))
          .toBe(true);
      expect(fileFinderResult.value.stat_entry.value.aff4path).toEqual({
        downloadUrl: downloadUrl,
        downloadParams: downloadParams,
        originalValue: originalFileFinderResult.value.stat_entry.value.aff4path,
        type: "__DownloadableUrn"
      });
    });

    it('replaces aff4path in ArtifactFilesDownloaderResult', function() {
      var original = angular.copy(artifactFilesDownloaderResult);

      expect(makeValueDownloadable(
          artifactFilesDownloaderResult, downloadUrl, downloadParams))
          .toBe(true);
      expect(artifactFilesDownloaderResult.value.downloaded_file.value.aff4path).toEqual({
        downloadUrl: downloadUrl,
        downloadParams: downloadParams,
        originalValue: original.value.downloaded_file.value.aff4path,
        type: "__DownloadableUrn"
      });
    });

    it('replaces aff4path recursively in ApiFlowResult', function() {
      var apiFlowResult = {
        value: {
          payload: angular.copy(statEntry)
        },
        type: 'ApiFlowResult'
      };
      expect(makeValueDownloadable(apiFlowResult, downloadUrl, downloadParams))
          .toBe(true);
      expect(apiFlowResult.value.payload.value.aff4path).toEqual({
        downloadUrl: downloadUrl,
        downloadParams: downloadParams,
        originalValue: statEntry.value.aff4path,
        type: "__DownloadableUrn"
      });
    });

    it('replaces aff4path recursively in ApiHuntResult', function() {
      var apiHuntResult = {
        value: {
          payload: angular.copy(statEntry)
        },
        type: 'ApiHuntResult'
      };
      expect(makeValueDownloadable(apiHuntResult, downloadUrl, downloadParams))
          .toBe(true);
      expect(apiHuntResult.value.payload.value.aff4path).toEqual({
        downloadUrl: downloadUrl,
        downloadParams: downloadParams,
        originalValue: statEntry.value.aff4path,
        type: "__DownloadableUrn"
      });
    });

    it('does nothing in other aff4 types', function() {
      var original = angular.copy(rdfstring);
      expect(makeValueDownloadable(rdfstring, downloadUrl, downloadParams))
          .toBe(false);
    });

    it('does nothing for other types wrapped in ApiFlowResult', function() {
      var apiFlowResult = {
        value: {
          payload: angular.copy(rdfstring)
        },
        type: 'ApiFlowResult'
      };
      expect(makeValueDownloadable(apiFlowResult, downloadUrl, downloadParams))
          .toBe(false);
    });

    it('does nothing for other types wrapped in ApiHuntResult', function() {
      var apiHuntResult = {
        value: {
          payload: angular.copy(rdfstring)
        },
        type: 'ApiHuntResult'
      };
      expect(makeValueDownloadable(apiHuntResult, downloadUrl, downloadParams))
          .toBe(false);
    });
  });

});
