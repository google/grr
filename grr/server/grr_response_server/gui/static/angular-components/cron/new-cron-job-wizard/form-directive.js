'use strict';

goog.module('grrUi.cron.newCronJobWizard.formDirective');
goog.module.declareLegacyNamespace();

const {DEFAULT_PLUGIN_URL} = goog.require('grrUi.hunt.newHuntWizard.formDirective');



/**
 * Controller for FormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
const FormController =
    function($scope, grrReflectionService, grrApiService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!Object<string, Object>} */
  this.descriptors_ = {};

  /** @private {?string} */
  this.defaultOutputPluginName;

  this.grrApiService_.get(DEFAULT_PLUGIN_URL).then(function(response) {
    if (angular.isDefined(response['data']['value'])) {
      this.defaultOutputPluginName = response['data']['value']['value'];
    }

    return this.grrReflectionService_.getRDFValueDescriptor(
        'CreateGenericHuntFlowArgs', true);
  }.bind(this)).then(function(descriptors) {
    angular.extend(this.descriptors_, descriptors);

    return this.grrReflectionService_.getRDFValueDescriptor(
        'ApiCronJob', true);
  }.bind(this)).then(function(descriptors) {
    angular.extend(this.descriptors_, descriptors);

    this.scope_.$watch('cronJob',
                       this.onCronJobChange_.bind(this));
  }.bind(this));

  // Aliasing hunt arguments which are themselves a part of
  // CreateAndRunGenericHuntFlow args - purely for convenience when
  // when using it in the template.
  this.scope_.$watch('cronJob.value.flow_args.value.hunt_args',
                     function(newValue) {
                       this.genericHuntArgs = newValue;
                     }.bind(this));

  // Aliasing hunt runner arguments which are themselves a part of
  // CreateAndRunGenericHuntFlow args - purely for convenience when
  // when using it in the template.
  this.scope_.$watch('cronJob.value.flow_args.value.hunt_runner_args',
                     function(newValue) {
                       this.huntRunnerArgs = newValue;
                     }.bind(this));

  this.scope_.$watch('cronJob.value.description.value',
                     this.onCronJobDescriptionChange_.bind(this));
};


/**
 * Called when cron job's description changes. Updates hunt's description.
 *
 * @param {?string} newValue New value.
 * @param {?string} oldValue Old value.
 * @private
 */
FormController.prototype.onCronJobDescriptionChange_ = function(
    newValue, oldValue) {
  if (newValue && this.huntRunnerArgs) {
    oldValue = oldValue || '';

    var huntDescription;
    if (angular.isDefined(this.huntRunnerArgs.value.description)) {
      huntDescription = this.huntRunnerArgs.value.description.value;
    }

    var cronSuffix = ' (cron)';
    if (angular.isUndefined(huntDescription) ||
        huntDescription == oldValue + cronSuffix) {
      this.huntRunnerArgs.value.description = {
        type: 'RDFString',
        value: newValue + cronSuffix
      };
    }
  }
};


/**
 * Called when 'genericHuntArgs' binding changes.
 *
 * @param {Object} newValue New binding value.
 * @private
 */
FormController.prototype.onCronJobChange_ = function(newValue) {
  /**
   * In order to make forms work, we have to make sure that all the structures
   * and values, that are going to be edited, are initialized to their
   * defaults.
   * TODO(user): This code is clunky and error-prone. Remove the need
   *     to specify ['value'] key every time. Make initialization a standard
   *     routine of grrReflectionService.
   */

  // If cronJob is not initialized, initialize it with default
  // ApiCronJob value.
  if (angular.isUndefined(newValue)) {
    newValue = this.scope_['cronJob'] =
        angular.copy(this.descriptors_['ApiCronJob']['default']);
  }

  // Flow name should always be CreateAndRunGenericHuntFlow.
  newValue['value']['flow_name'] = {
    type: 'RDFString',
    value: 'CreateAndRunGenericHuntFlow'
  };
  // If periodicity is not set, set it to 7 days.
  if (angular.isUndefined(newValue['value']['periodicity'])) {
    newValue['value']['periodicity'] = {
      type: 'Duration',
      value: 60 * 60 * 24 * 7
    };
  }
  // If lifetime is not set, set it to 1 hour.
  if (angular.isUndefined(newValue['value']['lifetime'])) {
    newValue['value']['lifetime'] = {
      type: 'Duration',
      value: 60 * 60 * 1
    };
  }
  // If flow arguments are not set, initialize them to CreateGenericHuntFlowArgs
  // default value.
  if (angular.isUndefined(newValue['value']['flow_args'])) {
    newValue['value']['flow_args'] =
        angular.copy(this.descriptors_['CreateGenericHuntFlowArgs']['default']);
  }
  var createHuntFlowArgs = newValue['value']['flow_args']['value'];

  // If CreateGenericHuntFlowArgs.hunt_args is not initialized, initialize
  // it to default GenericHuntArgs value.
  if (angular.isUndefined(createHuntFlowArgs['hunt_args'])) {
    createHuntFlowArgs['hunt_args'] =
        angular.copy(this.descriptors_['GenericHuntArgs']['default']);
  }

  var huntArgs = createHuntFlowArgs['hunt_args']['value'];
  // If CreateGenericHuntFlowArgs.hunt_args.flow_runner_args is not
  // initialized, initialize it to FlowRunnerArgs default.
  if (angular.isUndefined(huntArgs['flow_runner_args'])) {
    huntArgs['flow_runner_args'] = angular.copy(
        this.descriptors_['FlowRunnerArgs']['default']);
  }
  // If CreateGenericHuntFlowArgs.hunt_args.flow_runner_args.flow_name is not
  // initialized, initialize it to RDFString default.
  if (angular.isUndefined(huntArgs['flow_runner_args']['value']['flow_name'])) {
    huntArgs['flow_runner_args']['value']['flow_name'] =
        angular.copy(this.descriptors_['RDFString']['default']);
  }

  // If CreateGenericHuntFlowArgs.hunt_runner_args is not initialized,
  // initialize it to HuntRunnerArgs default.
  if (angular.isUndefined(createHuntFlowArgs['hunt_runner_args'])) {
    createHuntFlowArgs['hunt_runner_args'] =
        angular.copy(this.descriptors_['HuntRunnerArgs']['default']);
  }

  var huntRunnerArgs = createHuntFlowArgs['hunt_runner_args']['value'];
  // Initialize CreateGenericHuntFlowArgs.hunt_runner_args.client_rule_set
  if (angular.isUndefined(huntRunnerArgs['client_rule_set'])) {
    huntRunnerArgs['client_rule_set'] = angular.copy(
        this.descriptors_['ForemanClientRuleSet']['default']);
  }

  // If CreateGenericHuntFlowArgs.hunt_runner_args.output_plugins is
  // not initialized, initialize it to default output plugins list (if any).
  if (angular.isUndefined(huntRunnerArgs['output_plugins'])) {
    if (this.defaultOutputPluginName) {
      var defaultPluginDescriptor = angular.copy(
          this.descriptors_['OutputPluginDescriptor']['default']);
      defaultPluginDescriptor['value']['plugin_name'] = angular.copy(
          this.descriptors_['RDFString']['default']);
      defaultPluginDescriptor['value']['plugin_name']['value'] =
          this.defaultOutputPluginName;

      huntRunnerArgs['output_plugins'] = [defaultPluginDescriptor];
    } else {
      huntRunnerArgs['output_plugins'] = [];
    }
  }
};


/**
 * Sends cron creation request to the server.
 *
 * @export
 */
FormController.prototype.sendRequest = function() {
  this.grrApiService_.post('/cron-jobs', this.scope_['cronJob'], true).then(
      function resolve(response) {
        this.serverResponse = response;
        this.scope_['cronJob'] = response['data'];
      }.bind(this), function reject(response) {
        this.serverResponse = response;
        this.serverResponse['error'] = true;
      }.bind(this));
};


/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.FormDirective = function() {
  return {
    scope: {
      cronJob: '=?',

      onResolve: '&',
      onReject: '&'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/new-cron-job-wizard/' +
        'form.html',
    controller: FormController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.FormDirective.directive_name = 'grrNewCronJobWizardForm';
