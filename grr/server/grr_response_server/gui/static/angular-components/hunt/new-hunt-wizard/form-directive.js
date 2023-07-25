goog.module('grrUi.hunt.newHuntWizard.formDirective');
goog.module.declareLegacyNamespace();

const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');
const {ReflectionService} = goog.require('grrUi.core.reflectionService');


/** @const {string} */
exports.DEFAULT_PLUGINS_URL = '/config/' +
    'AdminUI.new_hunt_wizard.default_output_plugins';
const DEFAULT_PLUGINS_URL = exports.DEFAULT_PLUGINS_URL;



/**
 * Controller for FormDirective.
 * @unrestricted
 */
const FormController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!ReflectionService} grrReflectionService
   * @param {!ApiService} grrApiService
   * @ngInject
   */
  constructor($scope, grrReflectionService, grrApiService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!ReflectionService} */
    this.grrReflectionService_ = grrReflectionService;

    /** @private {!ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {!Object<string, Object>} */
    this.descriptors_ = {};

    /** @private {?string} */
    this.defaultOutputPluginNames;

    /** @type {boolean} */
    this.configureFlowPageHasErrors;

    this.grrApiService_.get(DEFAULT_PLUGINS_URL)
        .then(function(response) {
          if (angular.isDefined(response['data']['value'])) {
            this.defaultOutputPluginNames = response['data']['value']['value'];
          }

          return this.grrReflectionService_.getRDFValueDescriptor(
              'ApiCreateHuntArgs', true);
        }.bind(this))
        .then(function(descriptors) {
          angular.extend(this.descriptors_, descriptors);

          this.scope_.$watch(
              'createHuntArgs', this.onCreateHuntArgsChange_.bind(this));
        }.bind(this));
  }

  /**
   * Called when 'genericHuntArgs' binding changes.
   *
   * @param {Object} newValue New binding value.
   * @private
   */
  onCreateHuntArgsChange_(newValue) {
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
      if (this.defaultOutputPluginNames) {
        hra['value']['output_plugins'] = [];
        this.defaultOutputPluginNames.split(',').forEach((n) => {
          var defaultPluginDescriptor = angular.copy(
              this.descriptors_['OutputPluginDescriptor']['default']);
          defaultPluginDescriptor['value']['plugin_name'] =
              angular.copy(this.descriptors_['RDFString']['default']);
          defaultPluginDescriptor['value']['plugin_name']['value'] = n;

          hra['value']['output_plugins'].push(defaultPluginDescriptor);
        });
      } else if (angular.isUndefined(newValue['value']['output_plugins'])) {
        hra['value']['output_plugins'] = [];
      }
    }

    if (angular.isUndefined(hra['value']['client_rule_set'])) {
      hra['value']['client_rule_set'] =
          angular.copy(this.descriptors_['ForemanClientRuleSet']['default']);
    }
  }

  /**
   * Sends hunt creation request to the server.
   *
   * @export
   */
  sendRequest() {
    this.grrApiService_
        .post(
            '/hunts',
            /** @type {Object} */
            (stripTypeInfo(this.scope_['createHuntArgs'])))
        .then(
            function resolve(response) {
              this.serverResponse = response;
            }.bind(this),
            function reject(response) {
              this.serverResponse = response;
              this.serverResponse['error'] = true;
            }.bind(this));
  }

  /**
   * Called when the wizard resolves. Instead of directly calling the
   * scope callback, this controller method adds additional information (hunt
   * id) to the callback.
   *
   * @export
   */
  resolve() {
    var onResolve = this.scope_['onResolve'];
    if (onResolve && this.serverResponse) {
      var huntId = this.serverResponse['data']['value']['hunt_id']['value'];
      onResolve({huntId: huntId});
    }
  }
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
    scope: {createHuntArgs: '=?', onResolve: '&', onReject: '&'},
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
exports.FormDirective.directive_name = 'grrNewHuntWizardForm';
