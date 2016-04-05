'use strict';

goog.provide('grrUi.hunt.newHuntWizard.formDirective.DEFAULT_PLUGIN_URL');
goog.provide('grrUi.hunt.newHuntWizard.formDirective.FormController');
goog.provide('grrUi.hunt.newHuntWizard.formDirective.FormDirective');
goog.provide('grrUi.hunt.newHuntWizard.formDirective.USE_OO_HUNT_RULES_URL');

goog.scope(function() {

/** @const {string} */
grrUi.hunt.newHuntWizard.formDirective.DEFAULT_PLUGIN_URL = '/config/' +
    'AdminUI.new_hunt_wizard.default_output_plugin';
var DEFAULT_PLUGIN_URL =
    grrUi.hunt.newHuntWizard.formDirective.DEFAULT_PLUGIN_URL;

/** @const {string} */
grrUi.hunt.newHuntWizard.formDirective.USE_OO_HUNT_RULES_URL = '/config/' +
    'AdminUI.new_hunt_wizard.use_object_oriented_hunt_rules';
var USE_OO_HUNT_RULES_URL =
    grrUi.hunt.newHuntWizard.formDirective.USE_OO_HUNT_RULES_URL;

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

  /** @private {boolean} */
  this.ooHuntRulesEnabled;

  /** @private {boolean} */
  this.useOoHuntRulesDirective;

  this.grrApiService_.get(USE_OO_HUNT_RULES_URL).then(function(response) {
    this.ooHuntRulesEnabled = response['data']['value']['value'];
    if (angular.isString(this.useOoHuntRulesDirective)) {
      throw new Error('Got a string where boolean/integer was expected.');
    }
    this.ooHuntRulesEnabled = Boolean(this.ooHuntRulesEnabled);

    return this.grrApiService_.get(DEFAULT_PLUGIN_URL);
  }.bind(this)).then(function(response) {
    if (angular.isDefined(response['data']['value'])) {
      this.defaultOutputPluginName = response['data']['value']['value'];
    }

    return this.grrReflectionService_.getRDFValueDescriptor(
        'GenericHuntArgs', true);
  }.bind(this)).then(function(descriptors) {
    angular.extend(this.descriptors_, descriptors);

    return this.grrReflectionService_.getRDFValueDescriptor(
        'OutputPluginDescriptor', true);
  }.bind(this)).then(function(descriptors) {
    angular.extend(this.descriptors_, descriptors);

    return this.grrReflectionService_.getRDFValueDescriptor(
        'HuntRunnerArgs', true);
  }.bind(this)).then(function(descriptors) {
    angular.extend(this.descriptors_, descriptors);

    this.scope_.$watch('genericHuntArgs',
                       this.onGenericHuntArgsChange_.bind(this));
    this.scope_.$watch('huntRunnerArgs',
                       this.onHuntRunnerArgsChange_.bind(this));
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
FormController.prototype.onGenericHuntArgsChange_ = function(newValue) {
  if (angular.isUndefined(newValue)) {
    newValue = this.scope_['genericHuntArgs'] =
        angular.copy(this.descriptors_['GenericHuntArgs']['default']);
  }

  if (angular.isUndefined(newValue['value']['flow_runner_args'])) {
    newValue['value']['flow_runner_args'] =
        angular.copy(this.descriptors_['FlowRunnerArgs']['default']);
  }

  if (angular.isUndefined(
      newValue['value']['flow_runner_args']['value']['flow_name'])) {
    newValue['value']['flow_runner_args']['value']['flow_name'] =
        angular.copy(this.descriptors_['RDFString']['default']);
  }

  if (angular.isUndefined(newValue['value']['output_plugins'])) {
    if (this.defaultOutputPluginName) {
      var defaultPluginDescriptor = angular.copy(
          this.descriptors_['OutputPluginDescriptor']['default']);
      defaultPluginDescriptor['value']['plugin_name'] = angular.copy(
          this.descriptors_['RDFString']['default']);
      defaultPluginDescriptor['value']['plugin_name']['value'] =
          this.defaultOutputPluginName;

      newValue['value']['output_plugins'] = [defaultPluginDescriptor];
    } else if (angular.isUndefined(newValue['value']['output_plugins'])) {
      newValue['value']['output_plugins'] = [];
    }
  }
};

/**
 * Called when 'huntRunnerArgs' binding changes.
 *
 * @param {Object} newValue New binding value.
 * @private
 */
FormController.prototype.onHuntRunnerArgsChange_ = function(newValue) {
  if (angular.isUndefined(newValue)) {
    this.scope_['huntRunnerArgs'] = angular.copy(
        this.descriptors_['HuntRunnerArgs']['default']);
  }

  var huntRunnerArgs = this.scope_['huntRunnerArgs']['value'];

  if (angular.isUndefined(this.useOoHuntRulesDirective)) {
    this.useOoHuntRulesDirective = this.ooHuntRulesEnabled;

    if (angular.isDefined(huntRunnerArgs['client_rule_set'])) {
      if (angular.isDefined(
              huntRunnerArgs['client_rule_set']['value']['match_mode']) ||
          angular.isDefined(
              huntRunnerArgs['client_rule_set']['value']['rules'])) {
        this.useOoHuntRulesDirective = true;
      }
    }

    if (angular.isDefined(huntRunnerArgs['integer_rules']) &&
        huntRunnerArgs['integer_rules']['length'] > 0) {
      this.useOoHuntRulesDirective = false;
    }
    if (angular.isDefined(huntRunnerArgs['regex_rules']) &&
        huntRunnerArgs['regex_rules']['length'] > 0) {
      this.useOoHuntRulesDirective = false;
    }
  }

  if (this.useOoHuntRulesDirective) {
    if (angular.isUndefined(huntRunnerArgs['client_rule_set'])) {
      huntRunnerArgs['client_rule_set'] = angular.copy(
          this.descriptors_['ForemanClientRuleSet']['default']);
    }
  } else {
    if (angular.isUndefined(huntRunnerArgs['integer_rules'])) {
      huntRunnerArgs['integer_rules'] = [];
    }
    if (angular.isUndefined(huntRunnerArgs['regex_rules'])) {
      huntRunnerArgs['regex_rules'] = [];
    }
  }
};


/**
 * Sends hunt creation request to the server.
 *
 * @export
 */
FormController.prototype.sendRequest = function() {
  this.grrApiService_.post('/hunts/create', {
    hunt_runner_args: this.grrApiService_.stripTypeInfo(
        this.scope_['huntRunnerArgs']),
    hunt_args: this.grrApiService_.stripTypeInfo(
        this.scope_['genericHuntArgs'])
  }).then(function resolve(response) {
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
    var huntUrn = this.serverResponse['data']['hunt_id']['value'];
    onResolve({huntUrn: huntUrn});
  }
};


/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.newHuntWizard.formDirective.FormDirective = function() {
  return {
    scope: {
      genericHuntArgs: '=?',
      huntRunnerArgs: '=?',
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
