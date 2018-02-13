'use strict';

goog.module('grrUi.semantic.statExtFlagsLinuxDirective');
goog.module.declareLegacyNamespace();



/**
 * @typedef {{mask: number, symbol: string, description: string}}
 */
let Flag;

/**
 * @enum {string}
 */
const FlagsStatus = {
  MALFORMED: 'MALFORMED',
  SOME: 'SOME',
  NONE: 'NONE',
};

/**
 * An order of flag symbols as displayed by the Linux `lsattr` utility.
 *
 * The letters correspond to the symbol value of flags (defined below). Each
 * letter should be defined only once and should have exactly one matching flag.
 *
 * The order of flags is not really defined in any manpage and was extracted by
 * analysing source code of the `lsattr` utility.
 *
 * @type {string}
 */
const ORDER = 'suSDiadAcBZXEjItTehC';

/**
 * Descriptors of the extended flags for Linux file systems.
 *
 * Each descriptor contains three fields: mask, symbol and a short description.
 * Mask is a bitmask extracted directly from the Linux headers. Symbol is a
 * single letter used to represent this flag as displayed in `lsattr` and
 * `chattr` utilities. Finally, a description is a human-friendly short
 * description (extracted from comments in the Linux headers) presented to the
 * user as a on-hover hint.
 *
 * https://github.com/torvalds/linux/blob/master/include/linux/fs.h
 * https://github.com/mozilla-b2g/busybox/blob/master/e2fsprogs/old_e2fsprogs/e2p/pf.c
 *
 * @type {!Object<string, !Flag>}
 */
const FLAGS = {
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
    symbol: 'D',
    description: 'dirsync behaviour (directories only)',
  },
  'FS_TOPDIR_FL': {
    mask: 0x00020000,
    symbol: 'T',
    description: 'top of directory hierarchies',
  },
  'EXT4_HUGE_FILE_FL': {
    mask: 0x00040000,
    symbol: 'h',
    description: 'set to each huge file',
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

/**
 * @param {string} symbol
 * @return {!Flag}
 */
const getFlagBySymbol = function(symbol) {
  const flag = Object.values(FLAGS).find((flag) => flag.symbol === symbol);
  if (flag === undefined) {
    throw new Error(`unknown symbol: ${symbol}`);
  }
  return flag;
};

/**
 * @private
 * @param {number} mask
 * @return {!Array<?Flag>}
 */
const getMaskFlags = function(mask) {
  return ORDER.split('')
      .map(getFlagBySymbol)
      .map((flag) => (flag.mask & mask) !== 0 ? flag : null);
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
  this.flags = getMaskFlags(mask);
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
