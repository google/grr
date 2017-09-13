'use strict';

goog.provide('grrUi.forms.globExpressionsListFormDirective.GlobExpressionsListFormController');
goog.provide('grrUi.forms.globExpressionsListFormDirective.GlobExpressionsListFormDirective');


goog.scope(function() {

/**
 * Controller for GlobExpressionsListFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.forms.globExpressionsListFormDirective.GlobExpressionsListFormController =  function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  this.scope_.$watchGroup(['descriptor', 'value', 'field'],
                          this.onArgumentsChange_.bind(this));
};
var GlobExpressionsListFormController = grrUi.forms.globExpressionsListFormDirective
    .GlobExpressionsListFormController;


/**
 * Triggered on any bindings-related change. If the list rendered by this form
 * element is empty, inserts a new GlobExpression to render.
 *
 * @private
 */
GlobExpressionsListFormController.prototype.onArgumentsChange_ = function() {
  if (angular.isDefined(this.scope_['descriptor']) &&
      angular.isDefined(this.scope_['field']) &&
      angular.isDefined(this.scope_['value'])) {

    if (this.scope_['value'].length == 0) {
      var newGlob = angular.copy(this.scope_['descriptor']['default']);
      this.scope_['value'].push(newGlob);
    }
  }
};


/**
 * GlobExpressionsListFormController definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.forms.globExpressionsListFormDirective.GlobExpressionsListFormDirective =
    function() {
  return {
    restrict: 'E',
    scope: {
      descriptor: '=',
      value: '=',
      field: '='
    },
    templateUrl: '/static/angular-components/forms/' +
        'glob-expressions-list-form.html',
    controller: GlobExpressionsListFormController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.globExpressionsListFormDirective.GlobExpressionsListFormDirective
      .directive_name = 'grrGlobExpressionsListForm';

/**
 * Flag indicating that this custom repeated field directive should be rendered
 * without standard form label.
 *
 * @const
 * @export
 */
grrUi.forms.globExpressionsListFormDirective.GlobExpressionsListFormDirective
      .hideCustomTemplateLabel = true;


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.forms.globExpressionsListFormDirective.GlobExpressionsListFormDirective
    .semantic_type = 'GlobExpression';


});  // goog.scope
