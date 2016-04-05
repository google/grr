'use strict';

goog.provide('grrUi.core.basenameFilter.BasenameFilter');

goog.scope(function() {


/**
 * Filters input string, treating it as an URN and filtering out everything
 * except for the basename component.
 *
 * @param {string} input
 * @return {string} Basename component of the input string.
 * @export
 */
grrUi.core.basenameFilter.filterImplementation = function(input) {
  var components = input.split('/');
  return components[components.length - 1];
};


/**
 * Angular filter definition.
 *
 * @return {!Function}
 * @export
 * @ngInject
 */
grrUi.core.basenameFilter.BasenameFilter = function() {
  return grrUi.core.basenameFilter.filterImplementation;
};


/**
 * Name of the filter in Angular.
 *
 * @const
 * @export
 */
grrUi.core.basenameFilter.BasenameFilter.filter_name = 'grrBasename';

}); // goog.scope
