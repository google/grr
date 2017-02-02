'use strict';

goog.require('grrUi.core.fileDownloadUtils.getPathSpecFromValue');
goog.require('grrUi.core.fileDownloadUtils.makeValueDownloadable');
goog.require('grrUi.core.fileDownloadUtils.pathSpecToAff4Path');

describe('statEntryDirective.buildAff4Path', function() {
  var pathSpecToAff4Path = grrUi.core.fileDownloadUtils.pathSpecToAff4Path;

  it('converts os+tsk pathspec correctly', function() {
    var pathspec = {
      type: 'PathSpec',
      value: {
        path: { value: '\\\\.\\Volume{1234}\\', type: 'RDFString' },
        pathtype: { value: 'OS', type: 'EnumNamedValue' },
        mount_point: '/c:/',
        nested_path: {
          type: 'PathSpec',
          value: {
            path: { value: '/windows', type: 'RDFString' },
            pathtype: { value: 'TSK', type: 'EnumNamedValue' }
          }
        }
      }
    };

    expect(pathSpecToAff4Path(pathspec, 'C.1234567812345678'))
        .toBe('aff4:/C.1234567812345678/fs/tsk/\\\\.\\Volume{1234}\\/windows');
  });

  it('converts os+tsk ADS pathspec correctly', function() {
    var pathspec = {
      type: 'PathSpec',
      value: {
        path: { value: '\\\\.\\Volume{1234}\\', type: 'RDFString' },
        pathtype: { value: 'OS', type: 'EnumNamedValue' },
        mount_point: '/c:/',
        nested_path: {
          type: 'PathSpec',
          value: {
            path: { value: '/Test Directory/notes.txt:ads', type: 'RDFString' },
            pathtype: { value: 'TSK', type: 'EnumNamedValue' },
            inode: { value: 66, type: 'int' },
            ntfs_type: { value: 128, type: 'int'},
            ntfs_id: { value: 2, type: 'int'}
          }
        }
      }
    };

    expect(pathSpecToAff4Path(pathspec, 'C.1234567812345678'))
        .toBe('aff4:/C.1234567812345678/fs/tsk/\\\\.\\Volume{1234}\\/Test Directory/notes.txt:ads');
  });
});


describe('fileDownloadUtils', function() {
  var statEntry, fileFinderResult, artifactFilesDownloaderResult, rdfstring, pathspec;

  beforeEach(function() {
    pathspec = {
      value: {
        path: {
          type: 'RDFString',
          value: 'foo/bar',
        }
      },
      type: 'Pathspec'
    };

    statEntry = {
      value: {
        pathspec: pathspec,
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

  describe('getPathSpecFromValue', function() {
    var getPathSpecFromValue = grrUi.core.fileDownloadUtils.getPathSpecFromValue;

    it('returns null if argument is null or undefined', function() {
      expect(getPathSpecFromValue(null)).toBe(null);
      expect(getPathSpecFromValue(undefined)).toBe(null);
    });

    it('extracts pathspec from StatEntry', function() {
      expect(getPathSpecFromValue(statEntry)).toEqual(pathspec);
    });

    it('extracts pathspec from FileFinderResult', function() {
      expect(getPathSpecFromValue(fileFinderResult)).toEqual(pathspec);
    });

    it('extracts pathspec from ArtifactFilesDownloaderResult', function() {
      expect(getPathSpecFromValue(artifactFilesDownloaderResult)).toEqual(
          pathspec);
    });

    it('extracts pathspec recursively from ApiFlowResult', function() {
      var apiFlowResult = {
        value: {
          payload: angular.copy(statEntry)
        },
        type: 'ApiFlowResult'
      };
      expect(getPathSpecFromValue(apiFlowResult)).toEqual(pathspec);

      apiFlowResult = {
        value: {
          payload: angular.copy(fileFinderResult)
        },
        type: 'ApiFlowResult'
      };
      expect(getPathSpecFromValue(apiFlowResult)).toEqual(pathspec);

      apiFlowResult = {
        value: {
          payload: angular.copy(artifactFilesDownloaderResult)
        },
        type: 'ApiFlowResult'
      };
      expect(getPathSpecFromValue(apiFlowResult)).toEqual(pathspec);
    });

    it('extracts pathspec recursively from ApiHuntResult', function() {
      var apiHuntResult = {
        value: {
          payload: angular.copy(statEntry)
        },
        type: 'ApiHuntResult'
      };
      expect(getPathSpecFromValue(apiHuntResult)).toEqual(pathspec);

      apiHuntResult = {
        value: {
          payload: angular.copy(fileFinderResult)
        },
        type: 'ApiHuntResult'
      };
      expect(getPathSpecFromValue(apiHuntResult)).toEqual(pathspec);

      apiHuntResult = {
        value: {
          payload: angular.copy(artifactFilesDownloaderResult)
        },
        type: 'ApiHuntResult'
      };
      expect(getPathSpecFromValue(apiHuntResult)).toEqual(pathspec);
    });

    it('returns null for other aff4 types', function() {
      expect(getPathSpecFromValue(rdfstring)).toBe(null);
    });

    it('returns null for other types wrapped in ApiFlowResult', function() {
      var apiFlowResult = {
        value: {
          payload: angular.copy(rdfstring)
        },
        type: 'ApiFlowResult'
      };
      expect(getPathSpecFromValue(apiFlowResult)).toBe(null);
    });

    it('returns null for other types wrapped in ApiHuntResult', function() {
      var apiHuntResult = {
        value: {
          payload: angular.copy(rdfstring)
        },
        type: 'ApiHuntResult'
      };
      expect(getPathSpecFromValue(apiHuntResult)).toBe(null);
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
      expect(statEntry).toEqual({
        downloadUrl: downloadUrl,
        downloadParams: downloadParams,
        originalValue: originalStatEntry,
        type: "__DownloadableStatEntry"
      });
    });

    it('replaces aff4path in FileFinderResult', function() {
      var originalFileFinderResult = angular.copy(fileFinderResult);

      expect(makeValueDownloadable(
          fileFinderResult, downloadUrl, downloadParams))
          .toBe(true);
      expect(fileFinderResult.value.stat_entry).toEqual({
        downloadUrl: downloadUrl,
        downloadParams: downloadParams,
        originalValue: originalFileFinderResult.value.stat_entry,
        type: "__DownloadableStatEntry"
      });
    });

    it('replaces aff4path in ArtifactFilesDownloaderResult', function() {
      var original = angular.copy(artifactFilesDownloaderResult);

      expect(makeValueDownloadable(
          artifactFilesDownloaderResult, downloadUrl, downloadParams))
          .toBe(true);
      expect(artifactFilesDownloaderResult.value.downloaded_file).toEqual({
        downloadUrl: downloadUrl,
        downloadParams: downloadParams,
        originalValue: original.value.downloaded_file,
        type: "__DownloadableStatEntry"
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
      expect(apiFlowResult.value.payload).toEqual({
        downloadUrl: downloadUrl,
        downloadParams: downloadParams,
        originalValue: statEntry,
        type: "__DownloadableStatEntry"
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
      expect(apiHuntResult.value.payload).toEqual({
        downloadUrl: downloadUrl,
        downloadParams: downloadParams,
        originalValue: statEntry,
        type: "__DownloadableStatEntry"
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
