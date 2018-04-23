'use strict';

goog.module('grrUi.semantic.statExtFlagsLinuxDirective');
goog.module.declareLegacyNamespace();

const {Flag, LINUX_FLAGS_ORDERED} = goog.require('grrUi.client.extFlags');

/**
 * @enum {string}
 */
const FlagsStatus = {
  MALFORMED: 'MALFORMED',
  SOME: 'SOME',
  NONE: 'NONE',
};


/**
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const StatExtFlagsLinuxController =
    function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.value;
  this.scope_.$watch('::value', this.onValueChange.bind(this));

  /** @type {!FlagsStatus} */
  this.status = FlagsStatus.NONE;

  /** @type {!Array<?Flag>} */
  this.flags = [];
};


/**
 * @param {Object} value
 * @export
 */
StatExtFlagsLinuxController.prototype.onValueChange = function(value) {
  if (angular.isUndefined(value)) {
    return;
  }

  const mask = value.value;
  if (!Number.isInteger(mask) || mask < 0) {
    this.status = FlagsStatus.MALFORMED;
    return;
  }

  this.status = FlagsStatus.SOME;
  this.flags = LINUX_FLAGS_ORDERED.map((flag) => {
    return (flag.mask & mask) !== 0 ? flag : null;
  });
};


/**
 * @param {Function} $filter
 * @return {!angular.Directive}
 * @export
 */
exports.StatExtFlagsLinuxDirective = function($filter) {
  return {
    scope: {
      value: '=',
    },
    restrict: 'E',
    templateUrl:
        '/static/angular-components/semantic/stat-ext-flags-linux.html',
    controller: StatExtFlagsLinuxController,
    controllerAs: 'controller',
  };
};

const StatExtFlagsLinuxDirective = exports.StatExtFlagsLinuxDirective;

/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
StatExtFlagsLinuxDirective.directive_name = 'grrStatExtFlagsLinux';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
StatExtFlagsLinuxDirective.semantic_type = 'StatExtFlagsLinux';
