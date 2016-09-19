'use strict';

goog.require('grrUi.core.utils.camelCaseToDashDelimited');
goog.require('grrUi.core.utils.getLastPathComponent');
goog.require('grrUi.core.utils.stringToList');

describe('core utils', function() {

  describe('camelCaseToDashDelimited', function() {
    var camelCaseToDashDelimited = grrUi.core.utils.camelCaseToDashDelimited;

    it('returns a dash delimited string on camel case input', function() {
      var result = camelCaseToDashDelimited('someTestInput');
      expect(result).toBe('some-test-input');
    });

    it('replaces spaces with dashes', function() {
      var result = camelCaseToDashDelimited('some string with spaces');
      expect(result).toBe('some-string-with-spaces');
    });

    it('handles non-word characters by substitution with dash', function() {
      var result = camelCaseToDashDelimited('some string with $ symbols');
      expect(result).toBe('some-string-with-symbols');
    });

    it('handles uppercase abbreviations correctly', function() {
      var result = camelCaseToDashDelimited('someDDirectiveName');
      expect(result).toBe('some-d-directive-name');

      var result = camelCaseToDashDelimited('someDDDirectiveName');
      expect(result).toBe('some-d-d-directive-name');
    });

    it('handles string beginning with uppercase characters correctly', function() {
      var result = camelCaseToDashDelimited('SOMEUppercaseString');
      expect(result).toBe('s-o-m-e-uppercase-string');
    });
  });


  describe('stringToList', function() {
    var stringToList = grrUi.core.utils.stringToList;

    it('returns empty list for empty string', function() {
      var result = stringToList('');
      expect(result).toEqual([]);
    });

    it('splits 3 items correctly', function() {
      var result = stringToList('a, b, c');
      expect(result).toEqual(['a', 'b', 'c']);
    });

    it('trims spaces from elements', function() {
      var result = stringToList('a  , b  ,c ');
      expect(result).toEqual(['a', 'b', 'c']);
    });
  });

  describe('getLastPathComponent', function() {
    var getLastPathComponent = grrUi.core.utils.getLastPathComponent;

    it('returns empty string for an empty string', function() {
      expect(getLastPathComponent('')).toBe('');
    });

    it('returns correct last component', function() {
      expect(getLastPathComponent('foo')).toBe('foo');
      expect(getLastPathComponent('foo/bar')).toBe('bar');
      expect(getLastPathComponent('foo/bar/blah')).toBe('blah');
    });
  });
});
