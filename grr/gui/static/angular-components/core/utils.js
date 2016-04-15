'use strict';

goog.provide('grrUi.core.utils.camelCaseToDashDelimited');


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
grrUi.core.utils.camelCaseToDashDelimited = function(input) {
    return input.replace(/\W+/g, '-')
        .replace(/([A-Z])/g, '-$1')
        .replace(/^-+/, '') // Removing leading '-'.
        .replace(/-+$/, '') // Removing trailing '-'.
        .toLowerCase();
};