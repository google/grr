'use strict';

goog.module('grrUi.semantic.statExtFlagsOsxDirective');
goog.module.declareLegacyNamespace();



/**
 * @typedef {{mask: number, keyword: (string|undefined), description: string}}
 * @private
 */
let Flag;

/**
 * https://github.com/apple/darwin-xnu/blob/master/bsd/sys/stat.h
 *
 * @type {!Object<!string, !Flag>}
 * @private
 * @const
 */
const FLAGS = {
  'UF_NODUMP': {
    mask: 0x00000001,
    keyword: 'nodump',
    description: 'do not dump file',
  },
  'UF_IMMUTABLE': {
    mask: 0x00000002,
    keyword: 'uchg',
    description: 'file may not be changed',
  },
  'UF_APPEND': {
    mask: 0x00000004,
    keyword: 'uappnd',
    description: 'writes to file may only append',
  },
  'UF_OPAQUE': {
    mask: 0x00000008,
    keyword: 'opaque',
    description: 'directory is opaque wrt. union',
  },
  'UF_COMPRESSED': {
    mask: 0x00000020,
    keyword: undefined,
    description: 'file is compressed (some file-systems)',
  },
  'UF_TRACKED': {
    mask: 0x00000040,
    keyword: undefined,
    description: 'used for dealing with document ids',
  },
  'UF_DATAVAULT': {
    mask: 0x00000080,
    keyword: undefined,
    description: 'entitlement required for reading and writing',
  },
  'UF_HIDDEN': {
    mask: 0x00008000,
    keyword: 'hidden',
    description: 'hint that this item should not be displayed in a GUI',
  },
  'SF_ARCHIVED': {
    mask: 0x00010000,
    keyword: 'arch',
    description: 'file is archived',
  },
  'SF_IMMUTABLE': {
    mask: 0x00020000,
    keyword: 'schg',
    description: 'file may not be changed',
  },
  'SF_APPEND': {
    mask: 0x00040000,
    keyword: 'sappnd',
    description: 'writes to file may only append',
  },
  'SF_RESTRICTED': {
    mask: 0x00080000,
    keyword: undefined,
    description: 'entitlement required for writing',
  },
  'SF_NOUNLINK': {
    mask: 0x00100000,
    keyword: 'sunlnk',
    description: 'item may not be removed, renamed or mounted on',
  },
};


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
  this.flags = Object.values(FLAGS).filter((flag) => (flag.mask & mask) !== 0);
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
