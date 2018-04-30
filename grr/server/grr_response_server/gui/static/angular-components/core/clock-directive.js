'use strict';

goog.module('grrUi.core.clockDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ClockDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.timeService.TimeService} grrTimeService
 * @constructor
 * @ngInject
 */
const ClockController =
    function($scope, $interval, grrTimeService) {
  /** @private {grrUi.core.timeService.TimeService} */
  this.grrTimeService_ = grrTimeService;

  /** @type {string} The formatted clock to be displayed. */
  this.formattedClock;

  this.updateLiveClock_();
  $interval(this.updateLiveClock_.bind(this), 1000);
};


/**
 * Updates the clock based on the current time.
 *
 * @private
 */
ClockController.prototype.updateLiveClock_ =
    function() {
  this.formattedClock = this.grrTimeService_.formatAsUTC();
};

/**
 * Directive that displays RDFDatetime values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ClockDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    template: '<div class="navbar-text pull-right">' +
              '{$ controller.formattedClock $}' +
              '</div>',
    controller: ClockController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ClockDirective.directive_name = 'grrLiveClock';
