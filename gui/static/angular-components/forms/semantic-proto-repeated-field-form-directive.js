'use strict';

goog.provide('grrUi.forms.semanticProtoRepeatedFieldFormDirective.SemanticProtoRepeatedFieldFormController');
goog.provide('grrUi.forms.semanticProtoRepeatedFieldFormDirective.SemanticProtoRepeatedFieldFormDirective');


/**
 * Controller for SemanticProtoRepeatedFieldFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.forms.semanticProtoRepeatedFieldFormDirective
    .SemanticProtoRepeatedFieldFormController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;
};

var SemanticProtoRepeatedFieldFormController =
    grrUi.forms.semanticProtoRepeatedFieldFormDirective
    .SemanticProtoRepeatedFieldFormController;


/**
 * Handles clicks on 'Add' button.
 *
 * @export
 */
SemanticProtoRepeatedFieldFormController.prototype.addItem = function() {
  this.scope_.value.push(angular.copy(this.scope_.descriptor['default']));
};


/**
 * Handles clicks on 'Remove' buttons.
 *
 * @param {number} index Index of the element to remove.
 * @export
 */
SemanticProtoRepeatedFieldFormController.prototype.removeItem = function(
    index) {
  this.scope_.value.splice(index, 1);
};


/**
 * SemanticProtoRepeatedFieldFormDirective renders a form corresponding to a
 * repeated field of a RDFProtoStruct.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.semanticProtoRepeatedFieldFormDirective
    .SemanticProtoRepeatedFieldFormDirective = function() {
  return {
    scope: {
      value: '=',
      descriptor: '=',
      field: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/forms/' +
        'semantic-proto-repeated-field-form.html',
    controller: SemanticProtoRepeatedFieldFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.semanticProtoRepeatedFieldFormDirective
    .SemanticProtoRepeatedFieldFormDirective.directive_name =
    'grrFormProtoRepeatedField';
