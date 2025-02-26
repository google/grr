goog.module('grrUi.semantic.byteSizeDirective');
goog.module.declareLegacyNamespace();



/** @const {number} */
const KB_UNIT = 1024;

/** @const {number} */
const MB_UNIT = KB_UNIT * 1024;

/** @const {number} */
const GB_UNIT = MB_UNIT * 1024;


/**
 * Returns string representation of a given byte size value.
 *
 * @param {number} value Value in bytes to be stringified.
 * @return {!Array<number|string>} Array with a number and size token.
 */
const stringifyByteSize = function(value) {
  if (value == 0) {
    return [0, ''];
  }

  if (value > GB_UNIT) {
    return [value / GB_UNIT, 'GiB'];
  } else if (value > MB_UNIT) {
    return [value / MB_UNIT, 'MiB'];
  } else if (value > KB_UNIT) {
    return [value / KB_UNIT, 'KiB'];
  } else {
    return [value, 'B'];
  }
};


/**
 * Controller for ByteSizeDirective.
 * @unrestricted
 */
const ByteSizeController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @type {string} */
    this.stringifiedByteSize;

    this.scope_.$watch('::value', this.onValueChange.bind(this));
  }

  /**
   * Handles changes of scope.value attribute.
   *
   * @param {{type: string, value: number}|undefined} newValue
   *   An `rdf.ByteSize`-compatible object.
   */
  onValueChange(newValue) {
    if (!angular.isDefined(newValue)) {
      return;
    }

    const byteSize = newValue.value;
    if (angular.isNumber(byteSize)) {
      const stringified = stringifyByteSize(byteSize);
      const size = stringified[0];
      const sizeToken = stringified[1];

      const result = [Math.floor(size).toString()];
      const decimalPart = Math.round((size % 1) * 10).toString();
      if (decimalPart !== '0') {
        result.push('.', decimalPart);
      }
      result.push(sizeToken);

      this.stringifiedByteSize = result.join('');
    } else {
      this.stringifiedByteSize = '-';
    }
  }
};



/**
 * Directive that displays ByteSize values.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ByteSizeDirective = function() {
  return {
    scope: {value: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/byte-size.html',
    controller: ByteSizeController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.ByteSizeDirective.directive_name = 'grrByteSize';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.ByteSizeDirective.semantic_type = 'ByteSize';
