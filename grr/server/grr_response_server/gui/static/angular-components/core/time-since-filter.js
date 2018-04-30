'use strict';

goog.module('grrUi.core.timeSinceFilter');
goog.module.declareLegacyNamespace();



/**
 * Filters input, treating it as number of microseconds from epoch and
 * converting it into a string with a rough estimate of seconds/minutes/days
 * passed since the moment described by input.
 *
 * @param {grrUi.core.timeService.TimeService} grrTimeService
 * @param {number} input Time since epoch in microseconds.
 * @return {string} Human readable string with rough estimate of
 *     seconds/minutes/days passed since 'input' moment.
 */
const filterImplementation = function(grrTimeService, input) {
  var currentTimeMs = grrTimeService.getCurrentTimeMs();
  var inputTimeMs = input / 1000;

  if (inputTimeMs < 1e-6) {
    return '<invalid time value>';
  }

  var differenceSec = Math.abs(
      Math.round((currentTimeMs - inputTimeMs) / 1000));
  var measureUnit;
  var measureValue;
  if (differenceSec < 60) {
    measureUnit = 'seconds';
    measureValue = differenceSec;
  } else if (differenceSec < 60 * 60) {
    measureUnit = 'minutes';
    measureValue = Math.floor(differenceSec / 60);
  } else if (differenceSec < 60 * 60 * 24) {
    measureUnit = 'hours';
    measureValue = Math.floor(differenceSec / (60 * 60));
  } else {
    measureUnit = 'days';
    measureValue = Math.floor(differenceSec / (60 * 60 * 24));
  }

  if (currentTimeMs >= inputTimeMs) {
    return measureValue + ' ' + measureUnit + ' ago';
  } else {
    return 'in ' + measureValue + ' ' + measureUnit;
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
exports.TimeSinceFilter = function(grrTimeService) {
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
exports.TimeSinceFilter.filter_name = 'grrTimeSince';
