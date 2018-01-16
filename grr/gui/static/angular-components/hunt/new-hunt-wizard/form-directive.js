'use strict';

goog.provide('grrUi.hunt.newHuntWizard.formDirective.DEFAULT_PLUGIN_URL');
goog.provide('grrUi.hunt.newHuntWizard.formDirective.FormController');
goog.provide('grrUi.hunt.newHuntWizard.formDirective.FormDirective');
goog.require('grrUi.core.apiService.stripTypeInfo');

goog.scope(function() {

/** @const {string} */
grrUi.hunt.newHuntWizard.formDirective.DEFAULT_PLUGIN_URL = '/config/' +
    'AdminUI.new_hunt_wizard.default_output_plugin';
var DEFAULT_PLUGIN_URL =
    grrUi.hunt.newHuntWizard.formDirective.DEFAULT_PLUGIN_URL;

var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;

/**
 * Controller for FormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
grrUi.hunt.newHuntWizard.formDirective.FormController =
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

  /** @type {boolean} */
  this.configureFlowPageHasErrors;

  this.grrApiService_.get(DEFAULT_PLUGIN_URL).then(function(response) {
    if (angular.isDefined(response['data']['value'])) {
      this.defaultOutputPluginName = response['data']['value']['value'];
    }

    return this.grrReflectionService_.getRDFValueDescriptor(
        'ApiCreateHuntArgs', true);
  }.bind(this)).then(function(descriptors) {
    angular.extend(this.descriptors_, descriptors);

    this.scope_.$watch('createHuntArgs',
                       this.onCreateHuntArgsChange_.bind(this));
  }.bind(this));
};
var FormController =
    grrUi.hunt.newHuntWizard.formDirective.FormController;

/**
 * Called when 'genericHuntArgs' binding changes.
 *
 * @param {Object} newValue New binding value.
 * @private
 */
FormController.prototype.onCreateHuntArgsChange_ = function(newValue) {
  if (angular.isUndefined(newValue)) {
    newValue = this.scope_['createHuntArgs'] =
        angular.copy(this.descriptors_['ApiCreateHuntArgs']['default']);
  }

  if (angular.isUndefined(newValue['value']['flow_name'])) {
    newValue['value']['flow_name'] =
        angular.copy(this.descriptors_['RDFString']['default']);
  }

  var hra = newValue['value']['hunt_runner_args'];
  if (angular.isUndefined(hra)) {
    hra = newValue['value']['hunt_runner_args'] =
        angular.copy(this.descriptors_['HuntRunnerArgs']['default']);
  }

  if (angular.isUndefined(hra['value']['output_plugins'])) {
    if (this.defaultOutputPluginName) {
      var defaultPluginDescriptor = angular.copy(
          this.descriptors_['OutputPluginDescriptor']['default']);
      defaultPluginDescriptor['value']['plugin_name'] = angular.copy(
          this.descriptors_['RDFString']['default']);
      defaultPluginDescriptor['value']['plugin_name']['value'] =
          this.defaultOutputPluginName;

      hra['value']['output_plugins'] = [defaultPluginDescriptor];
    } else if (angular.isUndefined(newValue['value']['output_plugins'])) {
      hra['value']['output_plugins'] = [];
    }
  }

  if (angular.isUndefined(hra['value']['client_rule_set'])) {
    hra['value']['client_rule_set'] = angular.copy(
        this.descriptors_['ForemanClientRuleSet']['default']);
  }
};

/**
 * Sends hunt creation request to the server.
 *
 * @export
 */
FormController.prototype.sendRequest = function() {
  this.grrApiService_.post(
      '/hunts',
      /** @type {Object} */ (stripTypeInfo(this.scope_['createHuntArgs'])))
  .then(function resolve(response) {
    this.serverResponse = response;
  }.bind(this), function reject(response) {
    this.serverResponse = response;
    this.serverResponse['error'] = true;
  }.bind(this));
};


/**
 * Called when the wizard resolves. Instead of directly calling the
 * scope callback, this controller method adds additional information (hunt urn)
 * to the callback.
 *
 * @export
 */
FormController.prototype.resolve = function() {
  var onResolve = this.scope_['onResolve'];
  if (onResolve && this.serverResponse) {
    var huntUrn = this.serverResponse['data']['value']['urn']['value'];
    onResolve({huntUrn: huntUrn});
  }
};


/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.hunt.newHuntWizard.formDirective.FormDirective = function() {
  return {
    scope: {
      createHuntArgs: '=?',
      onResolve: '&',
      onReject: '&'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/new-hunt-wizard/form.html',
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
grrUi.hunt.newHuntWizard.formDirective.FormDirective.directive_name =
    'grrNewHuntWizardForm';

});  // goog.scope
