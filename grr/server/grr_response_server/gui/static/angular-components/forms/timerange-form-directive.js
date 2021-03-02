goog.module('grrUi.forms.timerangeFormDirective');
goog.module.declareLegacyNamespace();

const reflectionService = goog.requireType('grrUi.core.reflectionService');



/**
 * Controller for TimerangeFormDirective.
 * @unrestricted
 */
const TimerangeFormController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!reflectionService.ReflectionService}
   *     grrReflectionService
   * @ngInject
   */
  constructor($scope, grrReflectionService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!reflectionService.ReflectionService} */
    this.grrReflectionService_ = grrReflectionService;

    /** @type {number} */
    this.startTimeSecs;

    // The underlying proto expects microseconds.
    /** @type {Object} */
    this.formStartTime;

    /** @type {number} */
    this.durationSecs;

    // The underlying proto expects seconds.
    /** @type {Object} */
    this.formDuration;

    /** @type {string} */
    this.startTimeLabel;

    /** @type {string} */
    this.durationLabel;

    this.grrReflectionService_.getRDFValueDescriptor('RDFDatetime')
        .then(function(rdfDesc) {
          this.formStartTime = angular.copy(rdfDesc['default']);

          return this.grrReflectionService_.getRDFValueDescriptor(
              'DurationSeconds');
        }.bind(this))
        .then(function(rdfDesc) {
          this.formDuration = angular.copy(rdfDesc['default']);

          // these watchers require initialized typed fields
          this.scope_.$watchGroup(
              ['controller.startTimeSecs', 'controller.durationSecs'],
              this.onParamsChange_.bind(this));
          this.scope_.$watchGroup(
              [
                'controller.formStartTime.value',
                'controller.formDuration.value'
              ],
              this.onSubformsChange_.bind(this));

          // Ensure onParamsChange_ gets called first so the default values
          // don't override the given scope values.
          this.onParamsChange_([this.startTimeSecs, this.durationSecs]);
        }.bind(this));
  }

  /**
   * Handles changes to the scope parameters.
   *
   * @private
   */
  onParamsChange_([startTimeSecs, durationSecs]) {
    if (startTimeSecs !== null) {
      // Conversion to μs.
      this.formStartTime['value'] = startTimeSecs * 1e6;
    }

    if (durationSecs !== null) {
      // No conversion to μs, intentionally.
      this.formDuration['value'] = durationSecs;
    }
  }

  /**
   * Handles changes to the enclosed forms' parameters.
   *
   * @private
   */
  onSubformsChange_([formStartTime, formDuration]) {
    if (formStartTime !== null) {
      // Conversion to s.
      this.startTimeSecs = formStartTime / 1e6;
    }

    // No conversion necessary, both variables are in s.
    this.durationSecs = formDuration;
  }
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
