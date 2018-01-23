'use strict';

goog.provide('grrUi.semantic.objectLabelDirective.ObjectLabelDirective');

goog.scope(function() {


/**
 * Controller for ObjectLabelDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
const ObjectLabelController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @export {?string} */
  this.labelName;

  /** @export {?string} */
  this.labelOwner;

  this.scope_.$watch('::value', this.onValueChange_.bind(this));
};



/**
 * Handles changes of scope.value attribute.
 *
 * @param {number} newValue Label object (either fully typed or not).
 * @private
 */
ObjectLabelController.prototype.onValueChange_ = function(newValue) {
  if (!newValue) {
    this.labelName = this.labelType = null;
  }

  if (angular.isDefined(newValue['value'])) {
    // Passed value contains full type information.
    this.labelName = newValue['value']['name']['value'];
    this.labelOwner = newValue['value']['owner']['value'];
  } else {
    // Passed value doesn't have type information;
    this.labelName = newValue['name'];
    this.labelOwner = newValue['owner'];
  }
};



/**
 * Directive that displays AFF4 object label.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.semantic.objectLabelDirective.ObjectLabelDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/object-label.html',
    controller: ObjectLabelController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 */
grrUi.semantic.objectLabelDirective.ObjectLabelDirective.directive_name =
    'grrObjectLabel';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.objectLabelDirective.ObjectLabelDirective.semantic_type =
    'ClientLabel';


});  // goog.scope
