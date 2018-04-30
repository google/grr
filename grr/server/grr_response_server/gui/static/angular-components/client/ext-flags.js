'use strict';

goog.module('grrUi.client.extFlags');
goog.module.declareLegacyNamespace();


/**
 * @typedef {{
 *   name: string,
 *   identifier: string,
 *   mask: number,
 *   description: string
 * }}
 */
let Flag;

/**
 * Lookups a Linux flag descriptor based on a given identifier.
 *
 * @param {string} identifier A flag identifier to search for.
 * @return {!Flag} A flag with specified identifier.
 */
const getLinuxFlagByIdentifier = function(identifier) {
  const result = LINUX_FLAGS.find((flag) => flag.identifier == identifier);
  if (result === undefined) {
    throw new Error(`flag with identifier '${identifier}' not found`);
  }
  return result;
};

/**
 * Lookups a flag descriptor with specified name in given list of flags.
 *
 * @param {string} name A flag name to search for.
 * @param {!Array<!Flag>} flags An array of flags to search.
 * @return {!Flag} A flag with specified name.
 */
const getFlagByName = function(name, flags) {
  const result = flags.find((flag) => flag.name == name);
  if (result === undefined) {
    throw new Error(`flag with name '${name}' not found`);
  }
  return result;
};

/**
 * Lookups a Linux flag descriptor based on given name.
 *
 * @param {string} name A flag name to search for.
 * @return {!Flag} A flag with specified name.
 */
const getLinuxFlagByName = function(name) {
  return getFlagByName(name, LINUX_FLAGS);
};

/**
 * Lookups a macOS flag descriptor based on given name.
 *
 * @param {string} name A flag name to search for.
 * @return {!Flag} A flag with specified name.
 */
const getOsxFlagByName = function(name) {
  return getFlagByName(name, OSX_FLAGS);
};

/**
 * Lookups a mask of a Linux flag with particular name.
 *
 * @param {string} name A flag name to lookup the mask for.
 * @return {number} A mask of a flag with specified name.
 */
const getLinuxFlagMaskByName = function(name) {
  return getLinuxFlagByName(name).mask;
};

/**
 * Lookups a mask of a macOS flag with particular name.
 *
 * @param {string} name A flag name to lookup the mask for.
 * @return {number} A mask of a flag with specified name.
 */
const getOsxFlagMaskByName = function(name) {
  return getOsxFlagByName(name).mask;
};

/**
 * Calculates a mask for a set of Linux flags with specified name.
 *
 * @param {!Array<string>} names A set of names to calculate the mask for.
 * @return {number} A mask corresponding to the set of specified names.
 */
const getLinuxFlagMaskByNames = function(names) {
  return names.map(getLinuxFlagMaskByName).reduce((acc, mask) => acc | mask);
};

/**
 * Calculates a mask for a set of macOS flags with specified name.
 *
 * @param {!Array<string>} names A set of names to calculate the mask for.
 * @return {number} A mask corresponding to the set of specified names.
 */
const getOsxFlagMaskByNames = function(names) {
  return names.map(getOsxFlagMaskByName).reduce((acc, mask) => acc | mask);
};

/**
 * Descriptors of the extended flags for Linux file systems.
 *
 * Flag identifier is a single letter symbol used to represent this flag as
 * displayed in `lsattr` and `chattr` utilities.
 *
 * https://github.com/torvalds/linux/blob/master/include/linux/fs.h
 *
 * @type {!Array<!Flag>}
 */
const LINUX_FLAGS = [
  {
    name: 'FS_SECRM_FL',
    identifier: 's',
    mask: 0x00000001,
    description: 'secure deletion',
  },
  {
    name: 'FS_UNRM_FL',
    identifier: 'u',
    mask: 0x00000002,
    description: 'undelete',
  },
  {
    name: 'FS_COMPR_FL',
    identifier: 'c',
    mask: 0x00000004,
    description: 'compress file',
  },
  {
    name: 'FS_SYNC_FL',
    identifier: 'S',
    mask: 0x00000008,
    description: 'synchronous updates',
  },
  {
    name: 'FS_IMMUTABLE_FL',
    identifier: 'i',
    mask: 0x00000010,
    description: 'immutable file',
  },
  {
    name: 'FS_APPEND_FL',
    identifier: 'a',
    mask: 0x00000020,
    description: 'writes to file may only append',
  },
  {
    name: 'FS_NODUMP_FL',
    identifier: 'd',
    mask: 0x00000040,
    description: 'do not dump file',
  },
  {
    name: 'FS_NOATIME_FL',
    identifier: 'A',
    mask: 0x00000080,
    description: 'do not update atime',
  },
  {
    name: 'FS_DIRTY_FL',
    identifier: 'Z',
    mask: 0x00000100,
    description: 'compressed file is dirty',
  },
  {
    name: 'FS_COMPRBLK_FL',
    identifier: 'B',
    mask: 0x00000200,
    description: 'one or more compressed clusters',
  },
  {
    name: 'FS_NOCOMP_FL',
    identifier: 'X',
    mask: 0x00000400,
    description: 'do not compress',
  },
  {
    name: 'FS_ECOMPR_FL',
    identifier: 'E',
    mask: 0x00000800,
    description: 'compression error',
  },
  // {
  //   name: 'FS_BTREE_FL',
  //   identifier: undefined,
  //   mask: 0x00001000,
  //   description: 'btree format dir',
  // },
  {
    name: 'FS_INDEX_FL',
    identifier: 'I',
    mask: 0x00001000,
    description: 'hash-indexed directory',
  },
  // {
  //   name: 'FS_IMAGIC_FL',
  //   identifier: undefined,
  //   mask: 0x00002000,
  //   description: 'AFS directory',
  // },
  {
    name: 'FS_JOURNAL_DATA_FL',
    identifier: 'j',
    mask: 0x00004000,
    description: 'reserved for ext3',
  },
  {
    name: 'FS_NOTAIL_FL',
    identifier: 't',
    mask: 0x00008000,
    description: 'file tail should not be merged',
  },
  {
    name: 'FS_DIRSYNC_FL',
    identifier: 'D',
    mask: 0x00010000,
    description: 'dirsync behaviour (directories only)',
  },
  {
    name: 'FS_TOPDIR_FL',
    identifier: 'T',
    mask: 0x00020000,
    description: 'top of directory hierarchies',
  },
  {
    name: 'EXT4_HUGE_FILE_FL',
    identifier: 'h',
    mask: 0x00040000,
    description: 'set to each huge file',
  },
  {
    name: 'FS_EXTENT_FL',
    identifier: 'e',
    mask: 0x00080000,
    description: 'extents',
  },
  // {
  //   name: 'FS_DIRECTIO_FL',
  //   identifier: undefined,
  //   mask: 0x00100000,
  //   description: 'use direct I/O',
  // },
  {
    name: 'FS_NOCOW_FL',
    identifier: 'C',
    mask: 0x00800000,
    description: 'do not copy-on-write',
  },
];

/**
 * Descriptors of the extended flags for Linux file systems ordered as they
 * appear in the output of `lsattr`.
 *
 * The flag order is not really defined in any manpage and has been determined
 * by examining implementation of `lsattr`.
 *
 * https://github.com/mozilla-b2g/busybox/blob/master/e2fsprogs/old_e2fsprogs/e2p/pf.c
 * https://sourcecodebrowser.com/ldiskfsprogs/1.41.10/pf_8c_source.html
 *
 * @type {!Array<!Flag>}
 */
const LINUX_FLAGS_ORDERED =
    'suSDiadAcBZXEjItTehC'.split('').map(getLinuxFlagByIdentifier);

/**
 * Descriptors of the macOS extended flags.
 *
 * Flag identifier is a keyword as set by the `chflags` utility.
 *
 * https://github.com/apple/darwin-xnu/blob/master/bsd/sys/stat.h
 *
 * @type {!Array<!Flag>}
 */
const OSX_FLAGS = [
  {
    name: 'UF_NODUMP',
    identifier: 'nodump',
    mask: 0x00000001,
    description: 'do not dump file',
  },
  {
    name: 'UF_IMMUTABLE',
    identifier: 'uimmutable',
    mask: 0x00000002,
    description: 'file may not be changed',
  },
  {
    name: 'UF_APPEND',
    identifier: 'uappend',
    mask: 0x00000004,
    description: 'writes to file may only append',
  },
  {
    name: 'UF_OPAQUE',
    identifier: 'opaque',
    mask: 0x00000008,
    description: 'directory is opaque wrt. union',
  },
  // {
  //   name: 'UF_COMPRESSED',
  //   identifier: undefined,
  //   mask: 0x00000020,
  //   description: 'file is compressed (some file-systems)',
  // },
  // {
  //   name: 'UF_TRACKED',
  //   identifier: undefined,
  //   mask: 0x00000040,
  //   description: 'used for dealing with document ids',
  // },
  // {
  //   name: 'UF_DATAVAULT',
  //   identifier: undefined,
  //   mask: 0x00000080,
  //   description: 'entitlement required for reading and writing',
  // },
  {
    name: 'UF_HIDDEN',
    identifier: 'hidden',
    mask: 0x00008000,
    description: 'hint that this item should not be displayed in a GUI',
  },
  {
    name: 'SF_ARCHIVED',
    identifier: 'archived',
    mask: 0x00010000,
    description: 'file is archived',
  },
  {
    name: 'SF_IMMUTABLE',
    identifier: 'simmutable',
    mask: 0x00020000,
    description: 'file may not be changed',
  },
  {
    name: 'SF_APPEND',
    identifier: 'sappend',
    mask: 0x00040000,
    description: 'writes to file may only append',
  },
  // {
  //   name: 'SF_RESTRICTED',
  //   identifier: undefined,
  //   mask: 0x00080000,
  //   description: 'entitlement required for writing',
  // },
  {
    name: 'SF_NOUNLINK',
    identifier: 'sunlnk',
    mask: 0x00100000,
    description: 'item may not be removed, renamed or mounted on',
  },
];


exports.Flag = Flag;

exports.LINUX_FLAGS = LINUX_FLAGS;
exports.LINUX_FLAGS_ORDERED = LINUX_FLAGS_ORDERED;
exports.OSX_FLAGS = OSX_FLAGS;

exports.getLinuxFlagMaskByNames = getLinuxFlagMaskByNames;
exports.getOsxFlagMaskByNames = getOsxFlagMaskByNames;
