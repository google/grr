'use strict';

goog.module('grrUi.hunt.newHuntWizard.configureFlowPageDirective');
goog.module.declareLegacyNamespace();

const {valueHasErrors} = goog.require('grrUi.forms.utils');



/**
 * Controller for ConfigureFlowPageDirective.
 *
 * @param {!angular.Scope} $scope
 *
 * @constructor
 * @ngInject
 */
const ConfigureFlowPageController = function($scope) {
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


/**
 * @param {Object} newValue
 *
 * @private
 */
ConfigureFlowPageController.prototype.onFlowArgumentsDeepChange_ = function(
    newValue) {
  this.scope_['hasErrors'] = valueHasErrors(newValue);
};

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ConfigureFlowPageDirective = function() {
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
exports.ConfigureFlowPageDirective.directive_name = 'grrConfigureFlowPage';
