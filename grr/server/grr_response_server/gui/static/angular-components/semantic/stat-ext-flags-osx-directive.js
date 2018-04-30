'use strict';

goog.module('grrUi.semantic.statExtFlagsOsxDirective');
goog.module.declareLegacyNamespace();

const {Flag, OSX_FLAGS} = goog.require('grrUi.client.extFlags');


/**
 * @enum {string}
 * @private
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
const StatExtFlagsOsxController = function(
    $scope) {
  /**
   * @private {!angular.Scope}
   * @const
   */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.value;
  this.scope_.$watch('::value', this.onValueChange.bind(this));

  /** @type {!FlagsStatus} */
  this.status = FlagsStatus.NONE;

  /** @type {!Array<!Flag>} */
  this.flags = [];
};


// TODO(hanuszczak): Can we be more strict about the type of `value`?
/**
 * @param {!Object} value
 * @export
 */
StatExtFlagsOsxController.prototype.onValueChange = function(value) {
  if (angular.isUndefined(value)) {
    return;
  }

  const mask = value.value;
  if (!Number.isInteger(mask) || mask < 0) {
    this.status = FlagsStatus.MALFORMED;
    return;
  }

  this.status = FlagsStatus.SOME;
  this.flags = OSX_FLAGS.filter((flag) => (flag.mask & mask) !== 0);
};


/**
 * @param {!angular.$filter} $filter
 * @return {!angular.Directive}
 * @export
 */
exports.StatExtFlagsOsxDirective = function($filter) {
  return {
    scope: {
      value: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/stat-ext-flags-osx.html',
    controller: StatExtFlagsOsxController,
    controllerAs: 'controller',
  };
};

const StatExtFlagsOsxDirective = exports.StatExtFlagsOsxDirective;

/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
StatExtFlagsOsxDirective.directive_name = 'grrStatExtFlagsOsx';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
StatExtFlagsOsxDirective.semantic_type = 'StatExtFlagsOsx';
