'use strict';

goog.module('grrUi.flow.startFlowFormDirective');
goog.module.declareLegacyNamespace();

const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');
const {ReflectionService} = goog.require('grrUi.core.reflectionService');


/**
 * Controller for StartFlowFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!ApiService} grrApiService
 * @param {!ReflectionService} grrReflectionService
 * @ngInject
 */
const StartFlowFormController = function(
    $scope, grrApiService, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.clientId;

  /** @private {!ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {Object} */
  this.flowArguments;

  /** @type {Object} */
  this.flowRunnerArguments;

  /** @type {boolean} */
  this.requestSent = false;

  /** @type {?string} */
  this.responseError;

  /** @type {?string} */
  this.responseData;

  /** @type {Object} */
  this.outputPluginsField;

  /** @type {Object} */
  this.outputPluginDescriptor;

  /** @type {boolean} */
  this.flowFormHasErrors;

  this.scope_.$watch('descriptor', function(flowDescriptor) {
    this.requestSent = false;
    this.responseError = null;
    this.responseData = null;

    if (angular.isDefined(flowDescriptor)) {
      this.flowArguments = angular.copy(flowDescriptor['value']['default_args']);

      this.grrReflectionService_.getRDFValueDescriptor(
          'FlowRunnerArgs').then(function(descriptor) {
            this.flowRunnerArguments = angular.copy(descriptor['default']);
            this.flowRunnerArguments['value']['flow_name'] =
                flowDescriptor['value']['name'];
          }.bind(this));
    }
  }.bind(this));
};


/**
 * Sends API request to start a client flow.
 *
 * @export
 */
StartFlowFormController.prototype.startClientFlow = function() {
  var clientIdComponents = this.scope_['clientId'].split('/');
  var clientId;
  if (clientIdComponents[0] == 'aff4:') {
    clientId = clientIdComponents[1];
  } else {
    clientId = clientIdComponents[0];
  }

  this.grrApiService_.post('/clients/' + clientId + '/flows', {
    flow: {
      runner_args: stripTypeInfo(this.flowRunnerArguments),
      args: stripTypeInfo(this.flowArguments)
    }
  }).then(function success(response) {
    this.responseData = response['data'];
  }.bind(this), function failure(response) {
    this.responseError = response['data']['message'] || 'Unknown error';
  }.bind(this));
  this.requestSent = true;
};


/**
 * StartFlowFormDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
exports.StartFlowFormDirective = function() {
  return {
    scope: {
      clientId: '=?',
      descriptor: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/start-flow-form.html',
    controller: StartFlowFormController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.StartFlowFormDirective.directive_name = 'grrStartFlowForm';
