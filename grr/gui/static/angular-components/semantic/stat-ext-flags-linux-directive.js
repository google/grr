'use strict';

goog.provide('grrUi.semantic.statExtFlagsLinuxDirective.StatExtFlagsLinuxController');
goog.provide('grrUi.semantic.statExtFlagsLinuxDirective.StatExtFlagsLinuxDirective');

goog.scope(function() {

// https://github.com/torvalds/linux/blob/master/include/linux/fs.h
// https://github.com/mozilla-b2g/busybox/blob/master/e2fsprogs/old_e2fsprogs/e2p/pf.c
let ORDER = 'suSDiadAcBZXEjItTehC';
let FLAGS = {
  'FS_SECRM_FL': {
    mask: 0x00000001,
    symbol: 's',
    description: 'secure deletion',
  },
  'FS_UNRM_FL': {
    mask: 0x00000002,
    symbol: 'u',
    description: 'undelete',
  },
  'FS_COMPR_FL': {
    mask: 0x00000004,
    symbol: 'c',
    description: 'compress file',
  },
  'FS_SYNC_FL': {
    mask: 0x00000008,
    symbol: 'S',
    description: 'synchronous updates',
  },
  'FS_IMMUTABLE_FL': {
    mask: 0x00000010,
    symbol: 'i',
    description: 'immutable file',
  },
  'FS_APPEND_FL': {
    mask: 0x00000020,
    symbol: 'a',
    description: 'writes to file may only append',
  },
  'FS_NODUMP_FL': {
    mask: 0x00000040,
    symbol: 'd',
    description: 'do not dump file',
  },
  'FS_NOATIME_FL': {
    mask: 0x00000080,
    symbol: 'A',
    description: 'do not update atime',
  },
  'FS_DIRTY_FL': {
    mask: 0x00000100,
    symbol: 'Z',
    description: 'compressed file is dirty',
  },
  'FS_COMPRBLK_FL': {
    mask: 0x00000200,
    symbol: 'B',
    description: 'one or more compressed clusters',
  },
  'FS_NOCOMP_FL': {
    mask: 0x00000400,
    symbol: 'X',
    description: 'do not compress',
  },
  'FS_ECOMPR_FL': {
    mask: 0x00000800,
    symbol: 'E',
    description: 'compression error',
  },
  'FS_BTREE_FL': {
    mask: 0x00001000,
    symbol: undefined,
    description: 'btree format dir',
  },
  'FS_INDEX_FL': {
    mask: 0x00001000,
    symbol: 'I',
    description: 'hash-indexed directory',
  },
  'FS_IMAGIC_FL': {
    mask: 0x00002000,
    symbol: undefined,
    description: 'AFS directory',
  },
  'FS_JOURNAL_DATA_FL': {
    mask: 0x00004000,
    symbol: 'j',
    description: 'reserved for ext3',
  },
  'FS_NOTAIL_FL': {
    mask: 0x00008000,
    symbol: 't',
    description: 'file tail should not be merged',
  },
  'FS_DIRSYNC_FL': {
    mask: 0x00010000,
    symbol: undefined,
    description: 'dirsync behaviour (directories only)',
  },
  'FS_TOPDIR_FL': {
    mask: 0x00020000,
    symbol: 'T',
    description: 'top of directory hierarchies',
  },
  'FS_EXTENT_FL': {
    mask: 0x00080000,
    symbol: 'e',
    description: 'extents',
  },
  'FS_DIRECTIO_FL': {
    mask: 0x00100000,
    symbol: undefined,
    description: 'use direct I/O',
  },
  'FS_NOCOW_FL': {
    mask: 0x00800000,
    symbol: 'C',
    description: 'do not copy-on-write',
  },
};

// TODO(hanuszczak): Use `description` data to provide hints in the UI.


let maskToSymbols = function(mask) {
  let symbols = new Set();
  // FIXME(hanuszczak): We should use `for..of` loop here but Closure Compiler
  // complains here.
  for (let flag_name in FLAGS) {
    let flag = FLAGS[flag_name];
    if (mask & flag.mask) {
      symbols.add(flag.symbol);
    }
  }

  let result = '';
  // FIXME(hanuszczak): We should use `for..of` loop here. The code with a
  // `for..of` loop compiles fine but fails at runtime (only when used with
  // precompiled bundle).
  for (let i = 0; i < ORDER.length; i++) {
    let symbol = ORDER.charAt(i);
    result += symbols.has(symbol) ? symbol : '-';
  }
  return result;
};


/**
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 * @export
 */
grrUi.semantic.statExtFlagsLinuxDirective.StatExtFlagsLinuxController =
    function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.value;
  this.scope_.$watch('::value', this.onValueChange.bind(this));

  /** @type {string} */
  this.repr;
};

let StatExtFlagsLinuxController =
    grrUi.semantic.statExtFlagsLinuxDirective.StatExtFlagsLinuxController;

/**
 * @param {Object} value
 * @export
 */
StatExtFlagsLinuxController.prototype.onValueChange = function(value) {
  if (angular.isUndefined(value)) {
    this.repr = 'none';
    return;
  }

  let mask = value.value;
  if (!Number.isInteger(mask) || mask < 0) {
    this.repr = 'malformed';
  } else {
    this.repr = maskToSymbols(mask);
  }
};


/**
 * @param {Function} $filter
 * @return {!angular.Directive}
 * @export
 */
grrUi.semantic.statExtFlagsLinuxDirective.StatExtFlagsLinuxDirective = function(
    $filter) {
  return {
    scope: {
      value: '=',
    },
    restrict: 'E',
    template: '<span>{$ ::controller.repr $}</span>',
    controller: StatExtFlagsLinuxController,
    controllerAs: 'controller',
  };
};

let StatExtFlagsLinuxDirective =
    grrUi.semantic.statExtFlagsLinuxDirective.StatExtFlagsLinuxDirective;

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
});  // goog.scope
