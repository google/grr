'use strict';

goog.provide('grrUi.core.encodeUriComponentFilter.EncodeUriComponentFilter');

goog.scope(function() {


/**
 * Angular filter definition. Filter escapes given string using builtin
 * encodeURIComponent function.
 *
 * @return {!Function}
 * @export
 * @ngInject
 */
grrUi.core.encodeUriComponentFilter.EncodeUriComponentFilter = function() {
  return window.encodeURIComponent;
};


/**
 * Name of the filter in Angular.
 *
 * @const
 * @export
 */
grrUi.core.encodeUriComponentFilter.EncodeUriComponentFilter.filter_name =
    'grrEncodeUriComponent';

}); // goog.scope
