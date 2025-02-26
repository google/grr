goog.module('grrUi.semantic.hashListDirective');
goog.module.declareLegacyNamespace();



/**
 * @const {number} Size of each hash in the list, in bytes.
 */
const HASH_SIZE = 32;


/**
 * Controller for HashListDirective.
 * @unrestricted
 */
const HashListController = class {
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

    /** @type {!Array<Object>} */
    this.chunks = [];

    this.scope_.$watch('::value', this.onValueChange.bind(this));
  }

  /**
   * Handles changes of scope.value attribute. Splits the value into
   * chunks of 32 bytes to be passed to grr-hash-digest directives.
   *
   * @param {number} newValue Timestamp value in microseconds.
   * @suppress {missingProperties} as value can be anything.
   */
  onValueChange(newValue) {
    this.chunks = [];

    if (angular.isString(newValue.value)) {
      let bytes = this.window_.atob(newValue.value);
      while (bytes) {
        const chunkStr = bytes.substr(0, HASH_SIZE);
        bytes = bytes.substr(HASH_SIZE);

        this.chunks.push(
            {value: this.window_.btoa(chunkStr), type: 'HashDigest'});
      }
    }
  }
};



/**
 * Directive that displays a HashList value.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.HashListDirective = function() {
  return {
    scope: {value: '='},
    restrict: 'E',
    template: '<grr-semantic-value value="::controller.chunks"></grr-semantic-value>',
    controller: HashListController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.HashListDirective.directive_name = 'grrHashList';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.HashListDirective.semantic_type = 'HashList';
