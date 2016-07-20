'use strict';

goog.provide('grrUi.semantic.hashListDirective.HashListController');
goog.provide('grrUi.semantic.hashListDirective.HashListDirective');

goog.scope(function() {


/**
 * @const {number} Size of each hash in the list, in bytes.
 */
var HASH_SIZE = 32;


/**
 * Controller for HashListDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$window} $window
 * @constructor
 * @ngInject
 */
grrUi.semantic.hashListDirective.HashListController = function(
    $scope, $window) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$window} */
  this.window_ = $window;

  /** @type {!Array<Object>} */
  this.chunks = [];

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};

var HashListController =
    grrUi.semantic.hashListDirective.HashListController;


/**
 * Handles changes of scope.value attribute. Splits the value into
 * chunks of 32 bytes to be passed to grr-hash-digest directives.
 *
 * @param {number} newValue Timestamp value in microseconds.
 * @suppress {missingProperties} as value can be anything.
 */
HashListController.prototype.onValueChange = function(newValue) {
  this.chunks = [];

  if (angular.isString(newValue.value)) {
    var bytes = this.window_.atob(newValue.value);
    while (bytes) {
      var chunkStr = bytes.substr(0, HASH_SIZE);
      bytes = bytes.substr(HASH_SIZE);

      this.chunks.push({
        value: this.window_.btoa(chunkStr),
        type: 'HashDigest'
      });
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
grrUi.semantic.hashListDirective.HashListDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: '<grr-semantic-value value="::controller.chunks" />',
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
grrUi.semantic.hashListDirective.HashListDirective.directive_name =
    'grrHashList';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.hashListDirective.HashListDirective.semantic_type =
    'HashList';


});  // goog.scope
