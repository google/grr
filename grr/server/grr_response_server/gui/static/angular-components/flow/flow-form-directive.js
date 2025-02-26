goog.module('grrUi.flow.flowFormDirective');

const reflectionService = goog.requireType('grrUi.core.reflectionService');
const {ApiService} = goog.requireType('grrUi.core.apiService');
const {valueHasErrors} = goog.require('grrUi.forms.utils');


/** @const {string} */
exports.DEFAULT_PLUGINS_URL = '/config/' +
    'AdminUI.new_flow_form.default_output_plugins';
const DEFAULT_PLUGINS_URL = exports.DEFAULT_PLUGINS_URL;



/**
 * Controller for FlowFormDirective.
 * @unrestricted
 */
const FlowFormController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!reflectionService.ReflectionService}
   *     grrReflectionService
   * @param {!ApiService} grrApiService
   * @ngInject
   */
  constructor($scope, grrReflectionService, grrApiService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!reflectionService.ReflectionService} */
    this.grrReflectionService_ = grrReflectionService;

    /** @private @const {!ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {?string} */
    this.defaultOutputPluginNames;

    /** @type {Object} */
    this.outputPluginsField;

    /** @type {Object} */
    this.outputPluginDescriptor;

    this.grrApiService_.get(DEFAULT_PLUGINS_URL)
        .then(function(response) {
          if (angular.isDefined(response['data']['value']['value']['value']) &&
              response['data']['value']['value']['value']['value']) {
            this.defaultOutputPluginNames =
                response['data']['value']['value']['value']['value'];
          }
          return this.grrReflectionService_.getRDFValueDescriptor(
              'FlowRunnerArgs');
        }.bind(this))
        .then(function(descriptor) {
          angular.forEach(descriptor['fields'], function(field) {
            if (field.name == 'output_plugins') {
              this.outputPluginsField = field;
            }
          }.bind(this));

          return this.grrReflectionService_.getRDFValueDescriptor(
              'OutputPluginDescriptor');
        }.bind(this))
        .then(function(descriptor) {
          this.outputPluginDescriptor = descriptor;

          this.scope_.$watch(
              'flowRunnerArgs.value.output_plugins',
              this.onOutputPluginsChanged_.bind(this));
        }.bind(this));

    this.scope_.$watch(function() {
      return [this.scope_['flowArgs'], this.scope_['flowRunnerArgs']];
    }.bind(this), this.onArgsDeepChange_.bind(this), true);
  }

  /**
   * @private
   */
  onArgsDeepChange_() {
    this.scope_['hasErrors'] = valueHasErrors(this.scope_['flowArgs']) ||
        valueHasErrors(this.scope_['flowRunnerArgs']);
  }

  /**
   * Handles changes in output plugins part of flow runner args binding.
   * This function ensures that if withOutputPlugins binding is true, then
   * flowRunnerArgs.value.output_plugins is always set to a defined value.
   *
   * @param {Array<Object>} newValue New output plugins value.
   *
   * @private
   */
  onOutputPluginsChanged_(newValue) {
    if (!this.scope_['withOutputPlugins']) {
      return;
    }

    const fra = this.scope_['flowRunnerArgs'];
    if (angular.isUndefined(newValue) && angular.isDefined(fra)) {
      fra['value']['output_plugins'] = [];
      if (this.defaultOutputPluginNames) {
        this.defaultOutputPluginNames.split(',').forEach((n) => {
          const defaultPluginDescriptor = angular.copy(
            this.outputPluginDescriptor['default']
          );
          defaultPluginDescriptor['value']['plugin_name'] = {
            type: 'RDFString',
            value: n,
          };
          fra['value']['output_plugins'].push(defaultPluginDescriptor);
        });
      }
    }
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
