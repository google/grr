'use strict';

goog.module('grrUi.sidebar.clientWarningsDirective');
goog.module.declareLegacyNamespace();


/**
 * Checks if a given client label matches a given AdminUIClientWarningRule.
 *
 * @param {Object} label
 * @param {Object} rule
 * @return {boolean} True if there's a match, false otherwise.
 */
const checkIfLabelMatchesRule = (label, rule) => {
  const labelName = label['value']['name']['value'].toLowerCase();
  return rule['withLabels'].indexOf(labelName) != -1;
};


/**
 * Controller for ClientWarningsDirective..
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
const ClientWarningsController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!Array<Object>} */
  this.rules_ = [];

  /** @type {!Array<string>} */
  this.warnings = [];

  this.grrApiService_.getV2Cached('/config/AdminUI.client_warnings').then((response) => {
    const data = response['data'];
    if (data['value']) {
      this.rules_ = data['value']['rules'];
      for (const rule of this.rules_) {
        // Make sure we store all labels names as lowercase.
        rule['withLabels'] = rule['withLabels'].map(l => l.toLowerCase());
      }
    }
  }).then(() => {
    this.scope_.$watch('client', this.onClientChange_.bind(this));
  });
};


/**
 * Handles changes of scope.client attribute.
 *
 * @param {number} newValue Client object (with types or without)
 * @private
 */
ClientWarningsController.prototype.onClientChange_ = function(newValue) {
  this.warnings = [];

  if (angular.isUndefined(newValue) ||
      angular.isUndefined(newValue['value']['labels'])) {
    return;
  }

  for (let rule of this.rules_) {
    for (let label of newValue['value']['labels']) {
      if (checkIfLabelMatchesRule(label, rule)) {
        this.warnings.push(rule['message']);
        break;
      }
    }
  }
};


/**
 * Directive that displays per-client-label warnings configured by
 * GRR server's AdminUI.client_warnings configuration option.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ClientWarningsDirective = function() {
  return {
    scope: {
      client: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/sidebar/client-warnings.html',
    controller: ClientWarningsController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 */
exports.ClientWarningsDirective.directive_name = 'grrClientWarnings';
