'use strict';

goog.module('grrUi.core.encodeUriComponentFilter');
goog.module.declareLegacyNamespace();



/**
 * Angular filter definition. Filter escapes given string using builtin
 * encodeURIComponent function.
 *
 * @return {!Function}
 * @export
 * @ngInject
 */
exports.EncodeUriComponentFilter = function() {
  return window.encodeURIComponent;
};


/**
 * Name of the filter in Angular.
 *
 * @const
 * @export
 */
exports.EncodeUriComponentFilter.filter_name = 'grrEncodeUriComponent';
