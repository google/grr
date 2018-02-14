'use strict';

goog.module('grrUi.hunt.newHuntWizard.createHuntFromFlowFormDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for CreateHuntFromFlowFormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @constructor
 * @ngInject
 */
const CreateHuntFromFlowFormController =
    function($scope, grrApiService, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {Object} */
  this.createHuntArgs;

  /** @private {Object} */
  this.flow_;

  /** @private {!Object<string, Object>} */
  this.descriptors_ = {};

  this.grrReflectionService_.getRDFValueDescriptor(
      'ApiCreateHuntArgs', true).then(function(descriptors) {
    angular.extend(this.descriptors_, descriptors);

    this.scope_.$watchGroup(['flowId', 'clientId'],
                            this.onFlowIdClientIdChange_.bind(this));
  }.bind(this));
};



/**
 * Handles flowId/clientId attributes changes.
 *
 * @param {Array<string>} newValues
 * @private
 */
CreateHuntFromFlowFormController.prototype.onFlowIdClientIdChange_ = function(
    newValues) {
  if (newValues.every(angular.isDefined)) {
    var flowUrl = ['clients',
                   this.scope_['clientId'],
                   'flows',
                   this.scope_['flowId']].join('/');
    this.grrApiService_.get(flowUrl).then(function(response) {
      this.flow_ = response['data'];
    }.bind(this)).then(this.onFlowDataFetched_.bind(this));
  }
};

/**
 * Called when all flow data was fetched.
 *
 * @private
 */
CreateHuntFromFlowFormController.prototype.onFlowDataFetched_ = function() {
  var huntArgs = angular.copy(this.descriptors_['ApiCreateHuntArgs']['default']);
  huntArgs['value']['flow_name'] = angular.copy(
      this.flow_['value']['name']);
  huntArgs['value']['flow_args'] = angular.copy(this.flow_['value']['args']);

  huntArgs['value']['original_flow'] =
      angular.copy(this.descriptors_['FlowReference']['default']);
  huntArgs['value']['original_flow']['value']['flow_id'] =
      this.flow_['value']['flow_id']['value'];
  huntArgs['value']['original_flow']['value']['client_id'] =
      this.scope_['clientId'];

  this.createHuntArgs = huntArgs;
};


/**
 * Displays a new hunt wizard form with fields prefilled from a flow.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.CreateHuntFromFlowFormDirective = function() {
  return {
    scope: {
      flowId: '=',
      clientId: '=',
      onResolve: '&',
      onReject: '&'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/new-hunt-wizard/' +
        'create-hunt-from-flow-form.html',
    controller: CreateHuntFromFlowFormController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.CreateHuntFromFlowFormDirective.directive_name =
    'grrNewHuntWizardCreateFromFlowForm';
