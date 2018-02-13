'use strict';

goog.module('grrUi.core.timeService');
goog.module.declareLegacyNamespace();



/**
 * Service for time-related queries.
 *
 * @constructor
 * @ngInject
 * @export
 */
exports.TimeService = function() {};
var TimeService = exports.TimeService;


/**
 * Name of the service in Angular.
 */
TimeService.service_name = 'grrTimeService';


/**
 * Returns current time since epoch in milliseconds.
 *
 * @return {number} Number of milliseconds since epoch.
 */
TimeService.prototype.getCurrentTimeMs = function() {
  return new Date().getTime();
};

/**
 * Returns the time passed formatted as UTC for consumption by a human.
 *
 * @param {number} opt_timestamp The timestamp to format as UTC, in milliseconds
 *     from epoch. By default, the current timestamp is used,
 *     i.e. new Date() - 0
 *
 * @return {string} Formatted UTC time.
 */
TimeService.prototype.formatAsUTC = function(opt_timestamp) {
  var when = angular.isUndefined(opt_timestamp) ?
             moment() :
             moment(opt_timestamp);
  return when.utc().format('YYYY-MM-DD HH:mm:ss') + ' UTC';
};

/**
 * Returns a formatted delta between the given timestamp and the current time
 * for consumption by a human.
 *
 * @param {number} timestamp The timestamp to convert to delta format.
 *
 * @return {string} The formatted delta between the passed and the current time
 */
TimeService.prototype.getFormattedDiffFromCurrentTime = function(timestamp) {
  var diff = moment(timestamp).diff(moment());

  if (Math.abs(diff) < 60 * 1000) {
    return 'now';
  }

  return moment.duration(diff).humanize(true);
};
