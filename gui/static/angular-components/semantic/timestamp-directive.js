'use strict';

goog.provide('grrUi.semantic.timestampDirective.TimestampController');
goog.provide('grrUi.semantic.timestampDirective.TimestampDirective');

goog.require('grrUi.semantic.SemanticDirectivesRegistry');

goog.scope(function() {



/**
 * Controller for TimestampDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$filter} $filter
 * @constructor
 * @ngInject
 */
grrUi.semantic.timestampDirective.TimestampController = function(
    $scope, $filter) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?} */
  this.scope_.value;

  /** @private {!angular.$filter} $filter */
  this.filter_ = $filter;

  /** @private {string} */
  this.formattedTimestamp;

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

      this.formattedTimestamp = this.filter_('date')(
          timestamp, 'yyyy-MM-dd HH:mm:ss', 'UTC');
    }
  }
};



/**
 * Directive that displays RDFDatetime values.
 *
 * @constructor
 * @param {Function} $filter Angular filter provider.
 * @ngInject
 * @export
 */
grrUi.semantic.timestampDirective.TimestampDirective = function($filter) {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: '<nobr ng-if="::controller.formattedTimestamp !== undefined">' +
        '{$ ::controller.formattedTimestamp $}</nobr>',
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

grrUi.semantic.SemanticDirectivesRegistry.registerDirective(
    'RDFDatetime',
    grrUi.semantic.timestampDirective.TimestampDirective);


});  // goog.scope
