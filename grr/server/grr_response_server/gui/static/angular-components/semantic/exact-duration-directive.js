goog.module('grrUi.semantic.exactDurationDirective');
goog.module.declareLegacyNamespace();


/**
 * @typedef {{
 *   seconds: number,
 *   symbol: string,
 * }}
 */
let TimeUnit;

/** @type {!TimeUnit} */
const SECOND = {
  seconds: 1,
  symbol: 's',
};

/** @type {!TimeUnit} */
const MINUTE = {
  seconds: 60 * SECOND.seconds,
  symbol: 'm',
};

/** @type {!TimeUnit} */
const HOUR = {
  seconds: 60 * MINUTE.seconds,
  symbol: 'h',
};

/** @type {!TimeUnit} */
const DAY = {
  seconds: 24 * HOUR.seconds,
  symbol: 'd',
};

/** @type {!TimeUnit} */
const WEEK = {
  seconds: 7 * DAY.seconds,
  symbol: 'w',
};

/**
 * Converts number of seconds to more human-friendly representation.
 *
 * @param {number} seconds
 * @return {string}
 * @throws {Error} If provided number of seconds is negative.
 */
const stringifySeconds = function(seconds) {
  if (seconds < 0) {
    throw new Error(`Unexpected negative number: ${seconds}`);
  }
  seconds = Math.round(seconds);

  const components = [];

  for (const unit of [WEEK, DAY, HOUR, MINUTE, SECOND]) {
    const units = Math.floor(seconds / unit.seconds);
    seconds -= units * unit.seconds;

    if (units > 0) {
      components.push(`${units}${unit.symbol}`);
    }
  }

  if (components.length == 0) {
    return '0s';
  } else {
    return components.join(' ');
  }
};


/**
 * An Angular controller for formatting exact duration values.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
const ExactDurationController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?string} */
  this.stringifiedDuration = null;

  this.scope_.$watch('::value', (newValue) => this.onValueChange(newValue));
};

/**
 * Handles changes of the duration value.
 *
 * @param {{type: string, value: number}|undefined} newValue
 *   An `rdf.Datetime`-compatible object.
 */
ExactDurationController.prototype.onValueChange = function(newValue) {
  if (!angular.isDefined(newValue)) {
    return;
  }

  const duration = newValue.value;
  if (angular.isNumber(duration)) {
    this.stringifiedDuration = stringifySeconds(duration);
  } else {
    this.stringifiedDuration = '-';
  }
};


/**
 * An Angular directive that displays exact duration values.
 *
 * @return {!angular.Directive} Directive definition object.
 */
const ExactDurationDirective = function() {
  return {
    scope: {
      value: '=',
    },
    restrict: 'E',
    template: `
      <nobr ng-if="controller.stringifiedDuration">
        {$ ::controller.stringifiedDuration $}
      </nobr>
    `,
    controller: ExactDurationController,
    controllerAs: 'controller',
  };
};

/**
 * Name of the directive in Angular.
 *
 * @const
 */
ExactDurationDirective.directive_name = 'grrExactDuration';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 */
ExactDurationDirective.semantic_type = 'Duration';



exports.ExactDurationDirective = ExactDurationDirective;
