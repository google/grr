'use strict';

goog.provide('grrUi.flow.clientFlowsViewDirective.ClientFlowsViewController');
goog.provide('grrUi.flow.clientFlowsViewDirective.ClientFlowsViewDirective');

goog.scope(function() {


/**
 * Controller for ClientFlowsViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.flow.clientFlowsViewDirective.ClientFlowsViewController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.selectedFlowUrn;

  // TODO(user): use Angular service for this.
  if (angular.isDefined(grr.hash.flow)) {
    this.selectedFlowUrn = grr.hash.flow;
  }

  this.scope_.$watch('controller.selectedFlowUrn',
                     this.onSelectedFlowUrnChange_.bind(this));
};
var ClientFlowsViewController =
    grrUi.flow.clientFlowsViewDirective.ClientFlowsViewController;


/**
 * Handles selectedFlowUrn binding changes.
 *
 * @param {?string} newValue New binding value.
 * @private
 */
ClientFlowsViewController.prototype.onSelectedFlowUrnChange_ = function(
    newValue) {
  if (angular.isDefined(newValue)) {
    // TODO(user): use Angular service for this.
    grr.publish('hash_state', 'flow', this.selectedFlowUrn);
  }
};

/**
 * FlowsViewDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.flow.clientFlowsViewDirective.ClientFlowsViewDirective = function() {
  return {
    scope: {
      clientId: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/client-flows-view.html',
    controller: ClientFlowsViewController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.clientFlowsViewDirective.ClientFlowsViewDirective
    .directive_name = 'grrClientFlowsView';



});  // goog.scope
