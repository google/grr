goog.module('grrUi.semantic.statModeDirective');
goog.module.declareLegacyNamespace();

/*
 * TODO(hanuszczak): Some of the declarations below are unused. For now we
 * suppress the warning but it should be addressed at some point.
 */

/**
 * @fileoverview
 * @suppress {unusedLocalVariables}
 */


const S_IFMT = 61440;    // 0170000 type of file
const S_IFIFO = 4096;    // 0010000 named pipe
const S_IFCHR = 8192;    // 0020000 character device
const S_IFDIR = 16384;   // 0040000 directory
const S_IFBLK = 24576;   // 0060000 block device
const S_IFREG = 32768;   // 0100000 regular file
const S_IFLNK = 40960;   // 0120000 symbolic link
const S_IFSOCK = 49152;  // 0140000 socket
const S_IFWHT = 57344;   // 0160000 whiteout
const S_IMODE = 4095;    // 0007777 mode of file
const S_ISUID = 2048;    // 0004000 set user id
const S_ISGID = 1024;    // 0002000 set group id
const S_ISVTX = 512;     // 0001000 save swapped text even after use
const S_IRUSR = 256;     // 0000400 owner, read permission
const S_IWUSR = 128;     // 0000200 owner, write permission
const S_IXUSR = 64;      // 0000100 owner, execute/search permission
const S_IRGRP = 32;      // 0000040 group, read permission
const S_IWGRP = 16;      // 0000020 group, write permission
const S_IXGRP = 8;       // 0000010 group, execute/search permission
const S_IROTH = 4;       // 0000004 others, read permission
const S_IWOTH = 2;       // 0000002 others, write permission
const S_IXOTH = 1;       // 0000001 others, execute/search permission


/**
 * Controller for StatModeDirective.
 * @unrestricted
 */
const StatModeController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @type {?} */
    this.scope_.value;

    /** @type {string} */
    this.statMode;

    /** @type {string} */
    this.octalStatMode;

    this.scope_.$watch('::value', this.onValueChange.bind(this));
  }

  /**
   * Handles changes of scope.value attribute.
   *
   * @param {Object} newValue
   * @suppress {missingProperties} as value can be anything.
   */
  onValueChange(newValue) {
    if (!newValue || !angular.isNumber(newValue.value)) {
      this.octalStatMode = '-';
      this.statMode = '-';
    } else {
      const statMode = newValue.value;
      this.octalStatMode = this.calculateOctalMode_(statMode);
      this.statMode = this.calculateModeString_(statMode);
    }
  }

  /**
   * Calculates the octal representation of the stat mode.
   *
   * @param {number} statMode
   * @return {string} The octal representation of the stat mode.
   * @private
   */
  calculateOctalMode_(statMode) {
    return this.getMode_(statMode).toString(8);
  }

  /**
   * Calculates the string representation of the stat mode.
   *
   * @param {number} statMode
   * @return {string} The string representation of the stat mode.
   * @private
   */
  calculateModeString_(statMode) {
    let fileType = '-';
    if (this.isRegularFile_(statMode)) {
      fileType = '-';
    } else if (this.isBlockDevice_(statMode)) {
      fileType = 'b';
    } else if (this.isCharacterDevice_(statMode)) {
      fileType = 'c';
    } else if (this.isDirectory_(statMode)) {
      fileType = 'd';
    } else if (this.isFifo_(statMode)) {
      fileType = 'p';
    } else if (this.isLink_(statMode)) {
      fileType = 'l';
    } else if (this.isSocket_(statMode)) {
      fileType = 's';
    }

    let permissions = '';

    permissions += (statMode & S_IRUSR) ? 'r' : '-';
    permissions += (statMode & S_IWUSR) ? 'w' : '-';
    if (statMode & S_ISUID) {
      permissions += (statMode & S_IXUSR) ? 's' : 'S';
    } else {
      permissions += (statMode & S_IXUSR) ? 'x' : '-';
    }

    permissions += (statMode & S_IRGRP) ? 'r' : '-';
    permissions += (statMode & S_IWGRP) ? 'w' : '-';
    if (statMode & S_ISGID) {
      permissions += (statMode & S_IXGRP) ? 's' : 'S';
    } else {
      permissions += (statMode & S_IXGRP) ? 'x' : '-';
    }

    permissions += (statMode & S_IROTH) ? 'r' : '-';
    permissions += (statMode & S_IWOTH) ? 'w' : '-';
    if (statMode & S_ISVTX) {
      permissions += (statMode & S_IXOTH) ? 't' : 'T';
    } else {
      permissions += (statMode & S_IXOTH) ? 'x' : '-';
    }

    return fileType + permissions;
  }

  /**
   * Returns the mode part of the given stat mode.
   *
   * @param {number} mode
   * @return {number} The mode part of the stat mode.
   * @private
   */
  getMode_(mode) {
    return mode & S_IMODE;
  }

  /**
   * Returns the file type part of the given stat mode.
   *
   * @param {number} mode
   * @return {number} The type part of the stat mode.
   * @private
   */
  getType_(mode) {
    return mode & S_IFMT;
  }

  /**
   * Checks whether the type of the given mode is directory.
   *
   * @param {number} mode
   * @return {boolean} Whether the stat mode is a directory or not.
   * @private
   */
  isDirectory_(mode) {
    return this.getType_(mode) === S_IFDIR;
  }

  /**
   * Checks whether the type of the given mode is a character device.
   *
   * @param {number} mode
   * @return {boolean} Whether the stat mode is a character decive or not.
   * @private
   */
  isCharacterDevice_(mode) {
    return this.getType_(mode) === S_IFCHR;
  }

  /**
   * Checks whether the type of the given mode is block device.
   *
   * @param {number} mode
   * @return {boolean} Whether the stat mode is a block decive or not.
   * @private
   */
  isBlockDevice_(mode) {
    return this.getType_(mode) === S_IFBLK;
  }

  /**
   * Checks whether the type of the given mode is regular file.
   *
   * @param {number} mode
   * @return {boolean} Whether the stat mode is a regular file or not.
   * @private
   */
  isRegularFile_(mode) {
    return this.getType_(mode) === S_IFREG;
  }

  /**
   * Checks whether the type of the given mode is FIFO.
   *
   * @param {number} mode
   * @return {boolean} Whether the stat mode is a FIFO pipe or not.
   * @private
   */
  isFifo_(mode) {
    return this.getType_(mode) === S_IFIFO;
  }

  /**
   * Checks whether the type of the given mode is symbolic link.
   *
   * @param {number} mode
   * @return {boolean} Whether the stat mode is a link or not.
   * @private
   */
  isLink_(mode) {
    return this.getType_(mode) === S_IFLNK;
  }

  /**
   * Checks whether the type of the given mode is socket.
   *
   * @param {number} mode
   * @return {boolean} Whether the stat mode is a socket or not.
   * @private
   */
  isSocket_(mode) {
    return this.getType_(mode) === S_IFSOCK;
  }
};



/**
 * Directive that displays RDFDatetime values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @param {Function} $filter Angular filter provider.
 * @ngInject
 * @export
 */
exports.StatModeDirective = function($filter) {
  return {
    scope: {value: '='},
    restrict: 'E',
    template: '<abbr title="Mode {$ ::controller.octalStatMode $}">' +
        '  {$ ::controller.statMode $}' +
        '</abbr>',
    controller: StatModeController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.StatModeDirective.directive_name = 'grrStatMode';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.StatModeDirective.semantic_type = 'StatMode';
