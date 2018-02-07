'use strict';

goog.module('grrUi.client.virtualFileSystem.fileViewDirectiveTest');

const {getFileId, getFilePathFromId} = goog.require('grrUi.client.virtualFileSystem.fileViewDirective');


describe('file view directive', () => {
  describe('getFileId()', () => {

    it('returns the file id for any given path', () => {
      expect(getFileId('some/regular/path')).toEqual('_some-regular-path');
      expect(getFileId('some/$peci&l/path')).toEqual('_some-_24peci_26l-path');
      expect(getFileId('s0me/numb3r5/p4th')).toEqual('_s0me-numb3r5-p4th');
      expect(getFileId('a slightly/weird_/path')).toEqual('_a_20slightly-weird_5F-path');
      expect(getFileId('')).toEqual('_');
    });

    it('replaces characters with char code > 255 with more than a two-digit hex number',
       () => {
         expect(getFileId('some/sp€cial/path'))
             .toEqual('_some-sp_20ACcial-path');
         expect(getFileId('fs/os/c/中国新闻网新闻中'))
             .toEqual('_fs-os-c-_4E2D_56FD_65B0_95FB_7F51_65B0_95FB_4E2D');
       });
  });

  describe('getFilePathFromId()', () => {

    it('returns the path for any given id', () => {
      expect(getFilePathFromId('_some-regular-path')).toEqual('some/regular/path');
      expect(getFilePathFromId('_some-_24peci_26l-path')).toEqual('some/$peci&l/path');
      expect(getFilePathFromId('_s0me-numb3r5-p4th')).toEqual('s0me/numb3r5/p4th');
      expect(getFilePathFromId('_a_20slightly-weird_5F-path')).toEqual('a slightly/weird_/path');
      expect(getFilePathFromId('_')).toEqual('');
    });

    // The problem with _-based encoding is that it's ambiguous. It can't distinguish
    // a digit following an encoded character from a character encoded with more digits.
    // We limit number of digits we recognize to 2 to minimize potential conflicts.
    it('does not decode chars encoded with more than two hex-digits', () => {
      expect(getFilePathFromId('_some-sp_20ACcial-path')).not.toEqual('some/sp€cial/path');
      expect(getFilePathFromId('_fs-os-c-_4E2D_56FD_65B0_95FB_7F51_65B0_95FB_4E2D'))
          .not.toEqual('fs/os/c/中国新闻网新闻中');
    });
  });
});


exports = {};
