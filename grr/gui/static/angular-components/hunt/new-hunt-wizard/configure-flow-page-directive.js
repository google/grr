'use strict';

goog.provide('grrUi.hunt.newHuntWizard.configureFlowPageDirective.ConfigureFlowPageController');
goog.provide('grrUi.hunt.newHuntWizard.configureFlowPageDirective.ConfigureFlowPageDirective');
goog.require('grrUi.forms.utils.valueHasErrors');

goog.scope(function() {

var valueHasErrors = grrUi.forms.utils.valueHasErrors;

/**
 * Controller for ConfigureFlowPageDirective.
 *
 * @param {!angular.Scope} $scope
 *
 * @constructor
 * @ngInject
 */
grrUi.hunt.newHuntWizard.configureFlowPageDirective
    .ConfigureFlowPageController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Object} */
  this.flowDescriptor;

  this.scope_.$watch('controller.flowDescriptor', function(flowDescriptor) {
    if (angular.isUndefined(flowDescriptor)) {
      return;
    }

    this.scope_.flowName = flowDescriptor['value']['name']['value'];
    this.scope_['flowArguments'] = angular.copy(
        flowDescriptor['value']['default_args']);
  }.bind(this));

  this.scope_.$watch('flowArguments',
                     this.onFlowArgumentsDeepChange_.bind(this),
                     true);
};
var ConfigureFlowPageController =
    grrUi.hunt.newHuntWizard.configureFlowPageDirective
    .ConfigureFlowPageController;


ConfigureFlowPageController.prototype.onFlowArgumentsDeepChange_ = function(
    newValue) {
  this.scope_['hasErrors'] = valueHasErrors(newValue);
};

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.newHuntWizard.configureFlowPageDirective
    .ConfigureFlowPageDirective = function() {
  return {
    scope: {
      flowName: '=',
      flowArguments: '=',
      hasErrors: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/new-hunt-wizard/' +
        'configure-flow-page.html',
    controller: ConfigureFlowPageController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.newHuntWizard.configureFlowPageDirective
    .ConfigureFlowPageDirective.directive_name = 'grrConfigureFlowPage';

});  // goog.scope
