'use strict';

goog.provide('grrUi.flow.copyFlowFormDirective.CopyFlowFormController');
goog.provide('grrUi.flow.copyFlowFormDirective.CopyFlowFormDirective');
goog.require('grrUi.core.apiService.stripTypeInfo');

goog.scope(function() {

var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;

/**
 * Controller for CopyFlowFormDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
grrUi.flow.copyFlowFormDirective.CopyFlowFormController =
    function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {Object} */
  this.flow;

  this.scope_.$watchGroup(['flowId', 'clientId'],
                          this.onFlowIdClientIdChange_.bind(this));
};

var CopyFlowFormController =
    grrUi.flow.copyFlowFormDirective.CopyFlowFormController;


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
    }

  }).then(function success(response) {
    this.scope_['onResolve']({'flow': response['data']});
    return 'Flow was successfully launched!';

  }.bind(this), function failure(response) {
    var e = response['data']['message'] || 'Unknown error';
    this.scope_['onReject']({'error': e});
    return e;

  }.bind(this));
};

/**
 * Displays a "start flow" form with fills prefilled from the existing flow.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.flow.copyFlowFormDirective.CopyFlowFormDirective = function() {
  return {
    scope: {
      flowId: '=',
      clientId: '=',
      onResolve: '&',
      onReject: '&'
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
grrUi.flow.copyFlowFormDirective.CopyFlowFormDirective.directive_name =
    'grrCopyFlowForm';

});  // goog.scope
