'use strict';

goog.provide('grrUi.hunt.newHuntWizard.configureFlowPageDirective.ConfigureFlowPageController');
goog.provide('grrUi.hunt.newHuntWizard.configureFlowPageDirective.ConfigureFlowPageDirective');

goog.scope(function() {

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
};
var ConfigureFlowPageController =
    grrUi.hunt.newHuntWizard.configureFlowPageDirective
    .ConfigureFlowPageController;

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
      huntRunnerArgs: '='
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
