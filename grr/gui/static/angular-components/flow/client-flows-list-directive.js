'use strict';

goog.provide('grrUi.flow.clientFlowsListDirective.ClientFlowsListController');
goog.provide('grrUi.flow.clientFlowsListDirective.ClientFlowsListDirective');

goog.scope(function() {



/**
 * Controller for FlowsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$timeout} $timeout
 * @param {!angularUi.$modal} $modal
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
grrUi.flow.clientFlowsListDirective.ClientFlowsListController = function(
    $scope, $timeout, $modal, grrApiService, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$timeout} */
  this.timeout_ = $timeout;

  /** @private {!angularUi.$modal} */
  this.modal_ = $modal;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {?string} */
  this.flowsUrl;

  /**
   * This variable is bound to grr-flows-list's trigger-update attribute
   * and therefore is set by that directive to a function that triggers
   * list update.
   * @export {function()}
   */
  this.triggerUpdate;

  this.scope_.$watch('clientId', this.onClientIdChange_.bind(this));
};
var ClientFlowsListController =
    grrUi.flow.clientFlowsListDirective.ClientFlowsListController;


/**
 * Handles changes of clientId binding.
 *
 * @param {?string} newValue New binding value.
 * @private
 */
ClientFlowsListController.prototype.onClientIdChange_ = function(newValue) {
  if (angular.isString(newValue)) {
    var components = newValue.split('/');
    var basename = components[components.length - 1];
    this.flowsUrl = '/clients/' + basename + '/flows';
  } else {
    this.flowsUrl = null;
  }
};

/**
 * Handles clicks on 'Cancel Flow' button.
 *
 * @export
 */
ClientFlowsListController.prototype.cancelButtonClicked = function() {
  var components = this.scope_['selectedFlowUrn'].split('/');
  var cancelUrl = this.flowsUrl + '/' + components[components.length - 1] +
      '/actions/cancel';

  this.grrApiService_.post(cancelUrl, {}).then(function() {
    this.triggerUpdate();

    // This will force all the directives that depend on selectedFlowUrn
    // binding to refresh.
    var urn = this.scope_['selectedFlowUrn'];
    this.scope_['selectedFlowUrn'] = undefined;
    this.timeout_(function() {
      this.scope_['selectedFlowUrn'] = urn;
    }.bind(this), 0);
  }.bind(this));
};

/**
 * Shows 'New Hunt' dialog prefilled with the data of the currently selected
 * flow.
 *
 * @export
 */
ClientFlowsListController.prototype.createHuntFromFlow = function() {
  var huntUrn;

  var modalScope = this.scope_.$new();
  modalScope.flowUrn = this.scope_['selectedFlowUrn'];
  modalScope.resolve = function(newHuntUrn) {
    huntUrn = newHuntUrn;
    modalInstance.close();
  }.bind(this);
  modalScope.reject = function() {
    modalInstance.dismiss();
  }.bind(this);

  this.scope_.$on('$destroy', function() {
    modalScope.$destroy();
  });

  var modalInstance = this.modal_.open({
    template: '<grr-new-hunt-wizard-create-from-flow-form on-resolve="resolve(huntUrn)" ' +
        'on-reject="reject()" flow-urn="flowUrn" />',
    scope: modalScope,
    windowClass: 'wide-modal high-modal',
    size: 'lg'
  });
  modalInstance.result.then(function resolve() {
    var huntId = huntUrn.split('/')[2];
    this.grrRoutingService_.go('hunts', {huntId: huntId});
  }.bind(this));
};


/**
 * FlowsListDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.flow.clientFlowsListDirective.ClientFlowsListDirective = function() {
  return {
    scope: {
      clientId: '=',
      selectedFlowUrn: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/client-flows-list.html',
    controller: ClientFlowsListController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.clientFlowsListDirective.ClientFlowsListDirective
    .directive_name = 'grrClientFlowsList';



});  // goog.scope
