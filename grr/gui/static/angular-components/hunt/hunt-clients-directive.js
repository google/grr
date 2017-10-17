'use strict';

goog.provide('grrUi.hunt.huntClientsDirective.HuntClientsController');
goog.provide('grrUi.hunt.huntClientsDirective.HuntClientsDirective');

goog.scope(function() {


/**
 * Controller for HuntClientsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
grrUi.hunt.huntClientsDirective.HuntClientsController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @export {string} */
  this.huntClientsUrl;

  /** @export {string} */
  this.clientType = 'completed';

  this.scope_.$watchGroup(['huntUrn', 'controller.clientType'],
                          this.onHuntUrnOrClientTypeChange_.bind(this));
};

var HuntClientsController =
    grrUi.hunt.huntClientsDirective.HuntClientsController;


/**
 * Handles huntUrn attribute changes.
 *
 * @private
 */
HuntClientsController.prototype.onHuntUrnOrClientTypeChange_ = function() {
  var huntUrn = this.scope_['huntUrn'];

  if (!angular.isString(huntUrn) ||
      !angular.isString(this.clientType)) {
    return;
  }

  var components = huntUrn.split('/');
  var huntId = components[components.length - 1];
  this.huntClientsUrl = '/hunts/' + huntId + '/clients/' + this.clientType;
};


/**
 * Transforms the requested items for displaying.
 *
 * @param {Array<Object>} items to transform.
 * @return {Array<Object>} transformed items.
 *
 * @export
 */
HuntClientsController.prototype.transformItems = function(items) {
  angular.forEach(items, function(item) {
    var clientId = item['value']['client_id']['value'];
    var flowId = item['value']['flow_id']['value'];
    item.refParams = {clientId: clientId, flowId: flowId};
    item.flowRef = this.grrRoutingService_.href('client.flows', item.refParams);
  }.bind(this));

  return items;
};


/**
 * Handles clicks on flow links.
 *
 * @export
 */
HuntClientsController.prototype.onFlowClick = function(item) {
   this.grrRoutingService_.go('client.flows', item.refParams);
};



/**
 * Directive for displaying clients of a hunt with a given URN.
 *
 * @return {angular.Directive} Directive definition object.
 * @export
 */
grrUi.hunt.huntClientsDirective.HuntClientsDirective = function() {
  return {
    scope: {
      huntUrn: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-clients.html',
    controller: HuntClientsController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.huntClientsDirective.HuntClientsDirective.directive_name =
    'grrHuntClients';

});  // goog.scope
