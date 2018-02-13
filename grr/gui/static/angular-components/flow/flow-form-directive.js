'use strict';

goog.module('grrUi.flow.flowFormDirective');
goog.module.declareLegacyNamespace();

const {valueHasErrors} = goog.require('grrUi.forms.utils');


/**
 * Controller for FlowFormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @constructor
 * @ngInject
 */
const FlowFormController = function(
    $scope, grrReflectionService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {Object} */
  this.outputPluginsField;

  /** @type {Object} */
  this.outputPluginDescriptor;

  this.grrReflectionService_.getRDFValueDescriptor('FlowRunnerArgs').then(
      function(descriptor) {
        angular.forEach(descriptor['fields'], function(field) {
          if (field.name == 'output_plugins') {
            this.outputPluginsField = field;
          }
        }.bind(this));

        return this.grrReflectionService_.getRDFValueDescriptor(
            'OutputPluginDescriptor');
      }.bind(this)).then(function(descriptor) {
        this.outputPluginDescriptor = descriptor;
      }.bind(this));

  this.scope_.$watch('flowRunnerArgs.value.output_plugins',
                     this.onOutputPluginsChanged_.bind(this));

  this.scope_.$watch(function() {
    return [this.scope_['flowArgs'], this.scope_['flowRunnerArgs']];
  }.bind(this), this.onArgsDeepChange_.bind(this), true);
};


/**
 * @private
 */
FlowFormController.prototype.onArgsDeepChange_ = function() {
  this.scope_['hasErrors'] = valueHasErrors(this.scope_['flowArgs']) ||
      valueHasErrors(this.scope_['flowRunnerArgs']);
};

/**
 * Handles changes in output plugins part of flow runner args binding.
 * This function ensures that if withOutputPlugins binding is true, then
 * flowRunnerArgs.value.output_plugins is always set to a defined value.
 *
 * @param {Array<Object>} newValue New output plugins value.
 *
 * @private
 */
FlowFormController.prototype.onOutputPluginsChanged_ = function(newValue) {
  if (!this.scope_['withOutputPlugins']) {
    return;
  }

  var flowRunnerArgs = this.scope_['flowRunnerArgs'];
  if (angular.isUndefined(newValue) && angular.isDefined(flowRunnerArgs)) {
    flowRunnerArgs['value']['output_plugins'] = [];
  }
};


/**
 * Displays a form to edit the flow.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.FlowFormDirective = function() {
  return {
    scope: {
      flowArgs: '=',
      flowRunnerArgs: '=',
      withOutputPlugins: '=',
      hasErrors: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-form.html',
    controller: FlowFormController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.FlowFormDirective.directive_name = 'grrFlowForm';
