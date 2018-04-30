'use strict';

goog.module('grrUi.core.utilsTest');

const {camelCaseToDashDelimited, getLastPathComponent, stringToList} = goog.require('grrUi.core.utils');


describe('core utils', () => {
  describe('camelCaseToDashDelimited', () => {

    it('returns a dash delimited string on camel case input', () => {
      const result = camelCaseToDashDelimited('someTestInput');
      expect(result).toBe('some-test-input');
    });

    it('replaces spaces with dashes', () => {
      const result = camelCaseToDashDelimited('some string with spaces');
      expect(result).toBe('some-string-with-spaces');
    });

    it('handles non-word characters by substitution with dash', () => {
      const result = camelCaseToDashDelimited('some string with $ symbols');
      expect(result).toBe('some-string-with-symbols');
    });

    it('handles uppercase abbreviations correctly', () => {
      let result = camelCaseToDashDelimited('someDDirectiveName');
      expect(result).toBe('some-d-directive-name');

      result = camelCaseToDashDelimited('someDDDirectiveName');
      expect(result).toBe('some-d-d-directive-name');
    });

    it('handles string beginning with uppercase characters correctly', () => {
      const result = camelCaseToDashDelimited('SOMEUppercaseString');
      expect(result).toBe('s-o-m-e-uppercase-string');
    });
  });


  describe('stringToList', () => {

    it('returns empty list for empty string', () => {
      const result = stringToList('');
      expect(result).toEqual([]);
    });

    it('splits 3 items correctly', () => {
      const result = stringToList('a, b, c');
      expect(result).toEqual(['a', 'b', 'c']);
    });

    it('trims spaces from elements', () => {
      const result = stringToList('a  , b  ,c ');
      expect(result).toEqual(['a', 'b', 'c']);
    });
  });

  describe('getLastPathComponent', () => {

    it('returns empty string for an empty string', () => {
      expect(getLastPathComponent('')).toBe('');
    });

    it('returns correct last component', () => {
      expect(getLastPathComponent('foo')).toBe('foo');
      expect(getLastPathComponent('foo/bar')).toBe('bar');
      expect(getLastPathComponent('foo/bar/blah')).toBe('blah');
    });
  });
});


exports = {};
