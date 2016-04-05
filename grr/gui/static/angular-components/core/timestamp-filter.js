'use strict';

goog.provide('grrUi.core.timestampFilter.TimestampFilter');

goog.scope(function() {


/**
 * Converts the input to a date string.
 *
 * @param {grrUi.core.timeService.TimeService} grrTimeService
 * @param {number} value Timestamp value in microseconds.
 * @return {string} Date string.
 * @export
 */
grrUi.core.timestampFilter.filterImplementation = function(grrTimeService, value) {
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
grrUi.core.timestampFilter.TimestampFilter = function(grrTimeService) {
  return function(input) {
    return grrUi.core.timestampFilter.filterImplementation(grrTimeService, input);
  };
};


/**
 * Name of the filter in Angular.
 *
 * @const
 * @export
 */
grrUi.core.timestampFilter.TimestampFilter.filter_name = 'grrTimestamp';

}); // goog.scope
