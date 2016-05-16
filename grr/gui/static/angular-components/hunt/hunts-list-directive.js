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
grrUi.hunt.huntsListDirective.HuntsListController = function(
    $scope, $modal) {
  // Injected dependencies.

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angularUi.$modal} */
  this.modal_ = $modal;

  // Internal state.

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
   * and therefore is set by that directive to a function that triggers
   * table update.
   * @export {function()}
   */
  this.triggerUpdate;
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
  this.scope_['selectedHuntUrn'] = item.value.urn.value;
};


/**
 * Shows new hunt wizard.
 *
 * @export
 */
HuntsListController.prototype.newHunt = function() {
  var modalScope = this.scope_.$new();
  modalScope.resolve = function() {
    modalInstance.close();
  };
  modalScope.reject = function() {
    modalInstance.dismiss();
  };
  this.scope_.$on('$destroy', function() {
    modalScope.$destroy();
  });

  var modalInstance = this.modal_.open({
    template: '<grr-new-hunt-wizard-form on-resolve="resolve()" ' +
        'on-reject="reject()" />',
    scope: modalScope,
    windowClass: 'wide-modal high-modal',
    size: 'lg'
  });

  modalInstance.result.then(function resolve() {
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
        'query-params="{hunt_id: selectedHuntUrn}" />',
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
 * Shows 'Stop Hunt' confirmation dialog.
 *
 * @export
 */
HuntsListController.prototype.stopHunt = function() {
  var modalInstance = this.modal_.open({
    template: '<grr-legacy-renderer renderer="StopHuntConfirmationDialog" ' +
        'query-params="{hunt_id: selectedHuntUrn}" />',
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
        'query-params="{hunt_id: selectedHuntUrn}" />',
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
 * Shows 'New Hunt' dialog prefilled with the data of the currently selected
 * hunt.
 *
 * @export
 */
HuntsListController.prototype.copyHunt = function() {
  var modalScope = this.scope_.$new();
  modalScope.huntUrn = this.scope_['selectedHuntUrn'];
  modalScope.resolve = function() {
    modalInstance.close();
  };
  modalScope.reject = function() {
    modalInstance.dismiss();
  };

  this.scope_.$on('$destroy', function() {
    modalScope.$destroy();
  });

  var modalInstance = this.modal_.open({
    template: '<grr-new-hunt-wizard-copy-form on-resolve="resolve()" ' +
        'on-reject="reject()" hunt-urn="huntUrn" />',
    scope: modalScope,
    windowClass: 'wide-modal high-modal',
    size: 'lg'
  });
  modalInstance.result.then(function resolve() {
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
        'query-params="{hunt_id: selectedHuntUrn}" />',
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
 * Transforms table items before they get shown. Sets shortUrn to the last
 * component of hunt's URN and sets isRobot attribute based on hunt's creator.
 *
 * @param {!Array<Object>} items Items to be transformed.
 * @return {!Array<Object>} Transformed items.
 * @export
 * @suppress {missingProperties} For items, as they crom from JSON response.
 */
HuntsListController.prototype.transformItems = function(items) {
  angular.forEach(items, function(item) {
    item.shortUrn = item.value.urn.value.replace(/^aff4:\//, '');

    this.huntsByUrn[item.value.urn.value] = item;
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
    templateUrl: '/static/angular-components/hunt/hunts-list.html',
    controller: HuntsListController,
    controllerAs: 'controller'
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
