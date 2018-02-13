'use strict';

goog.module('grrUi.forms.timerangeFormDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for TimerangeFormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @constructor
 * @ngInject
 */
const TimerangeFormController =
    function($scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {number} */
  this.startTimeSecs;

  // The underlaying proto expects microseconds.
  /** @type {Object} */
  this.formStartTime;

  /** @type {number} */
  this.durationSecs;

  // The underlaying proto expects seconds.
  /** @type {Object} */
  this.formDuration;

  /** @type {string} */
  this.startTimeLabel;

  /** @type {string} */
  this.durationLabel;

  this.grrReflectionService_.getRDFValueDescriptor('RDFDatetime').then(
      function(rdfDesc) {
    this.formStartTime = angular.copy(rdfDesc['default']);

    return this.grrReflectionService_.getRDFValueDescriptor('Duration');
  }.bind(this)).then(function(rdfDesc) {
    this.formDuration = angular.copy(rdfDesc['default']);

    // these watchers require initialized typed fields
    this.scope_.$watchGroup(
        ['controller.startTimeSecs', 'controller.durationSecs'],
        this.onParamsChange_.bind(this));
    this.scope_.$watchGroup(
        ['controller.formStartTime.value', 'controller.formDuration.value'],
        this.onSubformsChange_.bind(this));

    // Ensure onParamsChange_ gets called first so the default values don't
    // override the given scope values.
    this.onParamsChange_();
  }.bind(this));

};


/**
 * Handles changes to the scope parameters.
 *
 * @private
 */
TimerangeFormController.prototype.onParamsChange_ = function() {
  if(angular.isDefined(this.startTimeSecs)) {
    // Conversion to μs.
    this.formStartTime['value'] = this.startTimeSecs * 1e6;
  }

  if(angular.isDefined(this.durationSecs)) {
    // No conversion to μs, intentionally.
    this.formDuration['value'] = this.durationSecs;
  }
};


/**
 * Handles changes to the enclosed forms' parameters.
 *
 * @private
 */
TimerangeFormController.prototype.onSubformsChange_ = function() {
  // Conversion to s.
  this.startTimeSecs = this.formStartTime['value'] / 1e6;

  // No conversion necessary, both variables are in s.
  this.durationSecs = this.formDuration['value'];
};


/**
 * Directive that displays a timerange selector.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.TimerangeFormDirective = function() {
  return {
    scope: {
      startTimeSecs: '=',
      durationSecs: '=',
      startTimeLabel: '=?',
      durationLabel: '=?'
    },
    bindToController: true,
    restrict: 'E',
    templateUrl: '/static/angular-components/forms/timerange-form.html',
    controller: TimerangeFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 */
exports.TimerangeFormDirective.directive_name = 'grrFormTimerange';
