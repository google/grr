'use strict';

goog.module('grrUi.core.timestampFilter');
goog.module.declareLegacyNamespace();



/**
 * Converts the input to a date string.
 *
 * @param {grrUi.core.timeService.TimeService} grrTimeService
 * @param {number} value Timestamp value in microseconds.
 * @return {string} Date string.
 */
const filterImplementation = function(grrTimeService, value) {
  if (angular.isNumber(value)) {
    var timestamp = value / 1000;
    return grrTimeService.formatAsUTC(timestamp);
  } else {
    return '-';
  }
};

/**
 * Angular filter definition.
 *
 * @param {grrUi.core.timeService.TimeService} grrTimeService
 * @return {!Function}
 * @export
 * @ngInject
 */
exports.TimestampFilter = function(grrTimeService) {
  return function(input) {
    return filterImplementation(grrTimeService, input);
  };
};


/**
 * Name of the filter in Angular.
 *
 * @const
 * @export
 */
exports.TimestampFilter.filter_name = 'grrTimestamp';
