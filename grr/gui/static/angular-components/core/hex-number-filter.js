'use strict';

goog.provide('grrUi.core.hexNumberFilter.HexNumberFilter');

goog.scope(function() {


/**
 * Converts the input number to a hex string representation.
 *
 * @param {number} input Number to show as hex string.
 * @return {string} Hex string representation of the input number. The return value is always
      a multiple of eight (with leading zeros if necessary) starting with 0x, e.g. 0x001234ff.
 * @export
 */
grrUi.core.hexNumberFilter.filterImplementation = function(input) {
  var hex = input.toString(16);

  var targetLength = Math.ceil(hex.length / 8) * 8;
  var leadingZeros = Array(targetLength - hex.length + 1).join(0);

  return '0x' + leadingZeros + hex;
};

/**
 * Angular filter definition.
 *
 * @return {!Function}
 * @export
 * @ngInject
 */
grrUi.core.hexNumberFilter.HexNumberFilter = function() {
  return function(input) {
    return grrUi.core.hexNumberFilter.filterImplementation(input);
  };
};


/**
 * Name of the filter in Angular.
 *
 * @const
 * @export
 */
grrUi.core.hexNumberFilter.HexNumberFilter.filter_name = 'grrHexNumber';

}); // goog.scope
