'use strict';

goog.module('grrUi.flow.copyFlowFormDirective');
goog.module.declareLegacyNamespace();

const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');


/**
 * Controller for CopyFlowFormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!ApiService} grrApiService
 * @constructor
 * @ngInject
 */
const CopyFlowFormController =
    function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {Object} */
  this.flow;

  /** @type {boolean} */
  this.flowFormHasErrors;

  this.scope_.$watchGroup(['flowId', 'clientId'],
                          this.onFlowIdClientIdChange_.bind(this));
};



/**
 * Handles flowId/clientId attribute changes.
 *
 * @param {Array<string>} newValues
 * @private
 */
CopyFlowFormController.prototype.onFlowIdClientIdChange_ = function(
    newValues) {
  if (newValues.every(angular.isDefined)) {
    var flowUrl = ['clients',
                   this.scope_['clientId'],
                   'flows',
                   this.scope_['flowId']].join('/');
    this.grrApiService_.get(flowUrl).then(function(response) {
      this.flow = response['data'];
    }.bind(this));
  }
};


/**
 * Handles clicks on dialog's 'proceed' button.
 *
 * @return {!angular.$q.Promise} Promise that resolves to a message that's
 *                               displayed in a dialog.
 * @export
 */
CopyFlowFormController.prototype.proceed = function() {
  var strippedFlow = stripTypeInfo(this.flow);

  return this.grrApiService_.post('clients/' + this.scope_['clientId'] + '/flows', {
    flow: {
      runner_args: strippedFlow['runner_args'],
      args: strippedFlow['args']
    },
    original_flow: {
      flow_id: this.scope_['flowId'],
      client_id: this.scope_['clientId']
    },
  }).then(function success(response) {
    this.scope_['onResolve']({'flow': response['data']});
    return 'Flow was successfully launched!';

  }.bind(this), function failure(response) {
    var e = response['data']['message'] || 'Unknown error';
    throw e;
  }.bind(this));
};

/**
 * Displays a "start flow" form with fills prefilled from the existing flow.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.CopyFlowFormDirective = function() {
  return {
    scope: {
      flowId: '=',
      clientId: '=',
      onResolve: '&',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/copy-flow-form.html',
    controller: CopyFlowFormController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.CopyFlowFormDirective.directive_name = 'grrCopyFlowForm';
