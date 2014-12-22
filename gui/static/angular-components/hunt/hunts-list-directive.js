'use strict';

goog.provide('grrUi.hunt.huntsListDirective.HuntsListController');
goog.provide('grrUi.hunt.huntsListDirective.HuntsListDirective');

goog.scope(function() {



/**
 * Controller for HuntsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angularUi.$modal} $modal Bootstrap UI modal service.
 * @ngInject
 */
grrUi.hunt.huntsListDirective.HuntsListController = function($scope, $modal) {
  // Injected dependencies.

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.selectedHuntUrn;

  /** @private {!angularUi.$modal} */
  this.modal_ = $modal;

  // Internal state.

  /**
   * Selected item in the list.
   * @export {string}
   */
  this.selectedHuntUrn;

  // TODO(user): use Angular service for this.
  if (angular.isDefined(grr.hash.hunt_id)) {
    this.selectedHuntUrn = grr.hash.hunt_id;
  }

  /**
   * Dictionary with hunts as values and urns as keys. Used to find currently
   * selected hunt object using selectedHuntUrn.
   * @export {!Object<string, Object>}
   */
  this.huntsByUrn = {};

  /**
   * If true, show hunts initiated by GRRWorker user.
   * @export {boolean}
   */
  this.showRobotHunts = false;

  /**
   * This variable is bound to grr-infinite-table's trigger-update attribute
   * and therefore is set but that directive to a function that triggers
   * table update.
   * @export {function()}
   */
  this.triggerUpdate;

  // Push the selection changes back to the scope, so that other UI components
  // can react on the change.
  this.scope_.$watch('ctrl.selectedHuntUrn', function() {
    this.scope_.selectedHuntUrn = this.selectedHuntUrn;

    // TODO(user): use Angular service for this.
    grr.publish('hash_state', 'hunt_id', this.selectedHuntUrn);
  }.bind(this));
};

var HuntsListController = grrUi.hunt.huntsListDirective.HuntsListController;


/**
 * Hunts list API url.
 * @const {string}
 */
HuntsListController.prototype.huntsUrl = '/hunts';


/**
 * Selects given item in the list.
 *
 * @param {!Object} item Item to be selected.
 * @export
 * @suppress {missingProperties} For items, as they crom from JSON response.
 */
HuntsListController.prototype.selectItem = function(item) {
  this.selectedHuntUrn = item.urn;
};


/**
 * Shows new hunt wizard.
 *
 * @export
 */
HuntsListController.prototype.newHunt = function() {
  var modalInstance = this.modal_.open({
    template: '<grr-legacy-renderer renderer="NewHunt" />',
    scope: this.scope_,
    windowClass: 'wide-modal high-modal',
    size: 'lg'
  });

  // TODO(user): there's no need to trigger update on dismiss.
  // Doing so only to maintain compatibility with legacy GRR code.
  // Remove as soon as legacy GRR code is removed.
  modalInstance.result.then(function resolve() {
    this.triggerUpdate();
  }.bind(this), function dismiss() {
    this.triggerUpdate();
  }.bind(this));
};


/**
 * Shows 'Run Hunt' confirmation dialog.
 *
 * @export
 */
HuntsListController.prototype.runHunt = function() {
  var modalInstance = this.modal_.open({
    template: '<grr-legacy-renderer renderer="RunHuntConfirmationDialog" ' +
        'query-params="{hunt_id: ctrl.selectedHuntUrn}" />',
    scope: this.scope_
  });

  // TODO(user): there's no need to trigger update on dismiss.
  // Doing so only to maintain compatibility with legacy GRR code.
  // Remove as soon as legacy GRR code is removed.
  modalInstance.result.then(function resolve() {
    this.triggerUpdate();
  }.bind(this), function dismiss() {
    this.triggerUpdate();
  }.bind(this));
};


/**
 * Shows 'Pause Hunt' confirmation dialog.
 *
 * @export
 */
HuntsListController.prototype.pauseHunt = function() {
  var modalInstance = this.modal_.open({
    template: '<grr-legacy-renderer renderer="PauseHuntConfirmationDialog" ' +
        'query-params="{hunt_id: ctrl.selectedHuntUrn}" />',
    scope: this.scope_
  });

  // TODO(user): there's no need to trigger update on dismiss.
  // Doing so only to maintain compatibility with legacy GRR code.
  // Remove as soon as legacy GRR code is removed.
  modalInstance.result.then(function resolve() {
    this.triggerUpdate();
  }.bind(this), function dismiss() {
    this.triggerUpdate();
  }.bind(this));
};


/**
 * Shows 'Modify Hunt' confirmation dialog.
 *
 * @export
 */
HuntsListController.prototype.modifyHunt = function() {
  var modalInstance = this.modal_.open({
    template: '<grr-legacy-renderer renderer="ModifyHuntDialog" ' +
        'query-params="{hunt_id: ctrl.selectedHuntUrn}" />',
    scope: this.scope_
  });

  // TODO(user): there's no need to trigger update on dismiss.
  // Doing so only to maintain compatibility with legacy GRR code.
  // Remove as soon as legacy GRR code is removed.
  modalInstance.result.then(function resolve() {
    this.triggerUpdate();
  }.bind(this), function dismiss() {
    this.triggerUpdate();
  }.bind(this));
};


/**
 * Shows 'Delete Hunt' confirmation dialog.
 *
 * @export
 */
HuntsListController.prototype.deleteHunt = function() {
  var modalInstance = this.modal_.open({
    template: '<grr-legacy-renderer renderer="DeleteHuntDialog" ' +
        'query-params="{hunt_id: ctrl.selectedHuntUrn}" />',
    scope: this.scope_
  });

  // TODO(user): there's no need to trigger update on dismiss.
  // Doing so only to maintain compatibility with legacy GRR code.
  // Remove as soon as legacy GRR code is removed.
  modalInstance.result.then(function resolve() {
    this.selectedHuntUrn = null;
    this.triggerUpdate();
  }.bind(this), function dismiss() {
    this.selectedHuntUrn = null;
    this.triggerUpdate();
  }.bind(this));
};


/**
 * Transforms table items before they get shown. Sets shortUrn to the last
 * component of hunt's URN and sets isRobot attribute based on hunt's creator.
 *
 * @param {Object} items Items to be transformed.
 * @export
 * @suppress {missingProperties} For items, as they crom from JSON response.
 */
HuntsListController.prototype.transformItems = function(items) {
  angular.forEach(items, function(item) {
    item.shortUrn = item.urn.replace(/^aff4:\//, '');
    item.isRobot = (item.attributes['aff4:flow_state'].
        context.creator == 'GRRWorker');

    this.huntsByUrn[item.urn] = item;
  }.bind(this));
  return items;
};


/**
 * Displays a table with list of available hunts.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.hunt.huntsListDirective.HuntsListDirective = function() {
  return {
    scope: {
      selectedHuntUrn: '=?'
    },
    restrict: 'E',
    templateUrl: 'static/angular-components/hunt/hunts-list.html',
    controller: HuntsListController,
    controllerAs: 'ctrl'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.huntsListDirective.HuntsListDirective.directive_name =
    'grrHuntsList';


});  // goog.scope
