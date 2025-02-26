goog.module('grrUi.semantic.bytesDirective');
goog.module.declareLegacyNamespace();

const {bytesToHexEncodedString} = goog.require('grrUi.forms.bytesFormDirective');


/**
 * Controller for BytesDirective.
 * @unrestricted
 */
const BytesController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.$window} $window
   * @ngInject
   */
  constructor($scope, $window) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.$window} */
    this.window_ = $window;

    /** @type {string} */
    this.stringifiedBytes;

    this.scope_.$watch('::value', this.onValueChange.bind(this));
  }

  /**
   * Handler for the click events.
   *
   * @param {?} e An event object.
   */
  onClick(e) {
    // onClick event should not be handleded by
    // anything other than this, otherwise the click
    // could be interpreted in the wrong way,
    // e.g. page could be redirected.
    e.stopPropagation();

    const bytes = this.scope_['value']['value'];
    try {
      this.stringifiedBytes = bytesToHexEncodedString(this.window_.atob(bytes));
    } catch (err) {
      this.stringifiedBytes = 'base64decodeerror(' + err.message + '):' + bytes;
    }
  }

  /**
   * Handles changes of scope.value attribute.
   *
   * @param {number} newValue Timestamp value in microseconds.
   * @suppress {missingProperties} as value can be anything.
   */
  onValueChange(newValue) {
    const bytes = newValue.value;
    if (angular.isString(bytes)) {
      if (bytes.length < FIRST_RENDER_LIMIT) {
        try {
          this.stringifiedBytes =
              bytesToHexEncodedString(this.window_.atob(bytes));
        } catch (err) {
          this.stringifiedBytes =
              'base64decodeerror(' + err.message + '):' + bytes;
        }
      }
    } else {
      this.stringifiedBytes = '';
    }
  }
};



/**
 * @const {number} Maximum number of bytes to render without showing a link.
 */
const FIRST_RENDER_LIMIT = 1024;



/**
 * Directive that displays Bytes values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.BytesDirective = function() {
  return {
    scope: {value: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/bytes.html',
    controller: BytesController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.BytesDirective.directive_name = 'grrBytes';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.BytesDirective.semantic_types = ['RDFBytes', 'bytes'];
