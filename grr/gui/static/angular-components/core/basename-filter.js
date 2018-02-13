'use strict';

goog.module('grrUi.core.basenameFilter');
goog.module.declareLegacyNamespace();



/**
 * Filters input string, treating it as an URN and filtering out everything
 * except for the basename component.
 *
 * @param {string} input
 * @return {string} Basename component of the input string.
 */
const filterImplementation = function(input) {
  if (!angular.isString(input)) {
    return input;
  } else {
    var components = input.split('/');
    return components[components.length - 1];
  }
};


/**
 * Angular filter definition.
 *
 * @return {!Function}
 * @export
 * @ngInject
 */
exports.BasenameFilter = function() {
  return filterImplementation;
};


/**
 * Name of the filter in Angular.
 *
 * @const
 * @export
 */
exports.BasenameFilter.filter_name = 'grrBasename';
