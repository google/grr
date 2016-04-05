'use strict';

goog.provide('grrUi.semantic.timestampDirective.TimestampController');
goog.provide('grrUi.semantic.timestampDirective.TimestampDirective');

goog.scope(function() {



/**
 * Controller for TimestampDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!grrUi.core.timeService.TimeService} grrTimeService
 * @constructor
 * @ngInject
 */
grrUi.semantic.timestampDirective.TimestampController = function(
    $scope, $element, grrTimeService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?} */
  this.scope_.value;

  /** @private {?string} */
  this.formattedTimestamp;

  /** @private {?number} */
  this.value;

  /** @private {!angular.jQuery} $element */
  this.element_ = $element;

  /** @private {grrUi.core.timeService.TimeService} grrTimeService */
  this.timeService_ = grrTimeService;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};

var TimestampController =
    grrUi.semantic.timestampDirective.TimestampController;


/**
 * Handles changes of scope.value attribute.
 *
 * @param {number} newValue Timestamp value in microseconds.
 * @suppress {missingProperties} as value can be anything.
 */
TimestampController.prototype.onValueChange = function(newValue) {
  if (angular.isDefined(newValue)) {
    if (newValue === null || newValue === 0) {
      this.formattedTimestamp = '-';
    } else {
      var timestamp;
      if (angular.isObject(newValue)) {
        timestamp = newValue.value / 1000;
      } else {
        timestamp = newValue / 1000;
      }

      this.value = timestamp;

      this.formattedTimestamp = this.timeService_.formatAsUTC(timestamp);
    }
  }
};

/**
 * Called when a user hovers the mouse over a timestamp to display the tooltip.
 */
TimestampController.prototype.onMouseEnter = function() {
  var span = $(this.element_).find('span')[0];

  if (angular.isDefined(this.value)) {
    span.title =
        this.timeService_.getFormattedDiffFromCurrentTime(Number(this.value));
  }
};

/**
 * Directive that displays RDFDatetime values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.timestampDirective.TimestampDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: '<span class="timestamp" ' +
        'ng-if="::controller.formattedTimestamp !== undefined" ' +
        'ng-mouseenter="controller.onMouseEnter()">' +
        '{$ ::controller.formattedTimestamp $}</span>',
    controller: TimestampController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.timestampDirective.TimestampDirective.directive_name =
    'grrTimestamp';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.timestampDirective.TimestampDirective.semantic_type =
    'RDFDatetime';


});  // goog.scope
