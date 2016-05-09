'use strict';

goog.provide('grrUi.flow.startFlowFormDirective.StartFlowFormController');
goog.provide('grrUi.flow.startFlowFormDirective.StartFlowFormDirective');
goog.require('grrUi.core.apiService.stripTypeInfo');

goog.scope(function() {

var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;

/**
 * Controller for StartFlowFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
grrUi.flow.startFlowFormDirective.StartFlowFormController = function(
    $scope, grrApiService, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.clientId;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
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
            this.flowRunnerArguments['value']['output_plugins'] = [];

            angular.forEach(descriptor['fields'], function(field) {
              if (field.name == 'output_plugins') {
                this.outputPluginsField = field;
              }
            }.bind(this));
          }.bind(this));
    }
  }.bind(this));

  this.grrReflectionService_.getRDFValueDescriptor(
      'OutputPluginDescriptor').then(function(descriptor) {
        this.outputPluginDescriptor = descriptor;
      }.bind(this));

};
var StartFlowFormController =
    grrUi.flow.startFlowFormDirective.StartFlowFormController;


/**
 * Handles "Launch" button clicks.
 *
 * @export
 */
StartFlowFormController.prototype.onLaunchButtonClick = function() {
  if (this.scope_['clientId']) {
    this.startClientFlow_();
  } else {
    this.startGlobalFlow_();
  }

};


/**
 * Sends API request to start a global flow.
 *
 * @private
 */
StartFlowFormController.prototype.startGlobalFlow_ = function() {
  this.grrApiService_.post('/flows', {
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
 * Sends API request to start a client flow.
 *
 * @private
 */
StartFlowFormController.prototype.startClientFlow_ = function() {
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
grrUi.flow.startFlowFormDirective.StartFlowFormDirective = function() {
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
grrUi.flow.startFlowFormDirective.StartFlowFormDirective.directive_name =
    'grrStartFlowForm';



});  // goog.scope
