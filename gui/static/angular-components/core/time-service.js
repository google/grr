'use strict';

goog.provide('grrUi.core.timeService.TimeService');

goog.scope(function() {



/**
 * Service for time-related queries.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.timeService.TimeService = function() {
};
var TimeService = grrUi.core.timeService.TimeService;


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


});  // goog.scope
