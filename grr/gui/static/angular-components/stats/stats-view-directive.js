'use strict';

goog.provide('grrUi.stats.statsViewDirective.StatsViewController');
goog.provide('grrUi.stats.statsViewDirective.StatsViewDirective');

goog.scope(function() {

/**
 * Controller for StatsViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.stats.statsViewDirective.StatsViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.selection;

  /** @type {boolean} */
  this.loaded;

  // Most jsTree instances are still rendered using the legacy GRR code. Until
  // all parts are migrated, the following event can be used to update URLs
  // based on tree selection.
  this.scope_.$on('grrTreeSelectionChanged', function(event, nodeId) {
    this.grrRoutingService_.go('stats', {selection: nodeId});
  }.bind(this));

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'selection',
      this.onSelectionChange_.bind(this));
};
var StatsViewController =
    grrUi.stats.statsViewDirective.StatsViewController;


/**
 * Handles changes to the selection state param.
 *
 * @param {string} selection The new selection.
 * @private
 */
StatsViewController.prototype.onSelectionChange_ = function(selection) {
  this.selection = selection;
  this.loaded = true;
};

/**
 * StatsViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.stats.statsViewDirective.StatsViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/stats/stats-view.html',
    controller: StatsViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.stats.statsViewDirective.StatsViewDirective.directive_name =
    'grrStatsView';

});  // goog.scope
