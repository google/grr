goog.module('grrUi.core.aff4ObjectRepresentationDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for the Aff4ObjectRepresentationDirective.
 * @unrestricted
 */
var Aff4ObjectRepresentationController = class {
  /**
   * @param {!angular.Scope} $scope Directive's scope.
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @type {?} */
    this.scope_.value;

    /** @export {?string} */
    this.aff4ObjectRepresentation;

    this.scope_.$watch('::value', this.onValueChange.bind(this));
  }

  /**
   * Handles value changes.
   *
   * @export
   */
  onValueChange() {
    if (angular.isObject(this.scope_.value)) {
      this.aff4ObjectRepresentation = this.scope_.value.value;
    } else {
      this.aff4ObjectRepresentation = this.scope_.value;
    }
  }
};



/**
 * Directive that displays given aff4 object and all its attributes.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.Aff4ObjectRepresentationDirective = function() {
  return {
    scope: {value: '='},
    restrict: 'E',
    templateUrl:
        '/static/angular-components/core/aff4-object-representation.html',
    controller: Aff4ObjectRepresentationController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.Aff4ObjectRepresentationDirective.directive_name =
    'grrAff4ObjectRepresentation';
