'use strict';

goog.module('grrUi.core.utils');
goog.module.declareLegacyNamespace();



/**
 * Regex that matches client ids.
 *
 * @const
 * @export
 */
exports.CLIENT_ID_RE = /^C\.[0-9a-fA-F]{16}$/;


/**
 * Converts camelCaseStrings to dash-delimited-strings.
 *
 * Examples:
 * "someTestInput" -> "some-test-input"
 * "some string with spaces" -> "some-string-with-spaces"
 * "some string with $ symbols" -> "some-string-with-symbols"
 * "someDDirectiveName" -> "some-d-directive-name"
 * "someDDDirectiveName" -> "some-d-d-directive-name"
 * "SOMEUppercaseString" -> "s-o-m-e-uppercase-string"
 *
 * @param {string} input String to be converted.
 * @return {string} Converted string.
 */
exports.camelCaseToDashDelimited = function(input) {
  return input.replace(/\W+/g, '-')
      .replace(/([A-Z])/g, '-$1')
      .replace(/^-+/, '')  // Removing leading '-'.
      .replace(/-+$/, '')  // Removing trailing '-'.
      .toLowerCase();
};


/**
 * Converts the given uppercase string to title case - capitalizes the first
 * letter, converts other letters to lowercase, replaces underscores with
 * spaces.
 *
 * Eg "CONSTANT_NAME" -> "Constant name"
 *
 * @param {string} input Uppercase string to be converted.
 * @return {string} Converted string.
 */
exports.upperCaseToTitleCase = function(input) {
  return (input.charAt(0).toUpperCase() +
          input.slice(1).toLowerCase()).replace(/_/g, ' ');
};


/**
 * Splits comma-separated string into a list of strings. Trims every string
 * along the way.
 *
 * @param {string} input Comma-separated string.
 * @return {Array<string>} List of trimmed strings.
 */
exports.stringToList = function(input) {
  var result = [];

  angular.forEach((input || '').split(','), function(item) {
    item = item.trim();
    if (item) {
      result.push(item);
    }
  });

  return result;
};


/**
 * Strips 'aff4:/' prefix from the string.
 *
 * @param {string} input
 * @return {string} String without 'aff4:/' prefix.
 */
exports.stripAff4Prefix = function(input) {
  var aff4Prefix = 'aff4:/';
  if (input.toLowerCase().indexOf(aff4Prefix) == 0) {
    return input.substr(aff4Prefix.length);
  } else {
    return input;
  }
};


/**
 * Gets last path component (components are separated by '/') from the
 * string.
 *
 * @param {string} input
 * @return {string} The last path component of the input.
 */
exports.getLastPathComponent = function(input) {
  var components = input.split('/');
  return components[components.length - 1];
};
