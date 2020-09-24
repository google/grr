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

/** @unrestricted */
const StatExtFlagsOsxController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
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
  }

  /**
   * @param {{type: string, value: number}|undefined} value
   * @export
   */
  onValueChange(value) {
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
  }
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
