'use strict';

goog.module('grrUi.hunt.huntsListDirective');
goog.module.declareLegacyNamespace();

const {AclDialogService} = goog.require('grrUi.acl.aclDialogService');
const {ApiService} = goog.require('grrUi.core.apiService');
const {DialogService} = goog.require('grrUi.core.dialogService');
const {stripAff4Prefix} = goog.require('grrUi.core.utils');


/**
 * Controller for HuntsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$q} $q
 * @param {!angularUi.$uibModal} $uibModal Bootstrap UI modal service.
 * @param {DialogService} grrDialogService
 * @param {!ApiService} grrApiService
 * @param {!AclDialogService} grrAclDialogService
 * @ngInject
 */
const HuntsListController = function(
    $scope, $q, $uibModal, grrDialogService, grrApiService,
    grrAclDialogService) {
  // Injected dependencies.

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!angularUi.$uibModal} */
  this.uibModal_ = $uibModal;

  /** @private {DialogService} */
  this.grrDialogService_ = grrDialogService;

  /** @private {!ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!AclDialogService} */
  this.grrAclDialogService_ = grrAclDialogService;

  // Internal state.

  /**
   * Dictionary with hunts as values and ids as keys. Used to find currently
   * selected hunt object using selectedHuntId.
   * @export {!Object<string, Object>}
   */
  this.huntsById = {};

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



/**
 * Hunts list API url.
 * @const {string}
 */
HuntsListController.prototype.huntsUrl = '/hunts';


/**
 * Computes an URL to currently selected hunt.
 *
 * @return {string} URL to the selected hunt.
 *
 * @private
 */
HuntsListController.prototype.buildHuntUrl_ = function() {
  var components = this.scope_['selectedHuntId'].split('/');
  var basename = components[components.length - 1];
  return this.huntsUrl + '/' + basename;
};


/*
 * TODO(hanuszczak): The method below looks like a duplication with
 * `CronJobsListController.wrapApiPromise_`. Maybe these can be merged into one
 * method instead?
 */

/**
 * @param {!angular.$q.Promise} promise A promise to wrap.
 * @param {string} successMessage Message to return on success.
 * @return {!angular.$q.Promise} Wrapped promise.
 *
 * @private
 */
HuntsListController.prototype.wrapApiPromise_ = function(promise, successMessage) {
    return promise.then(
        function success() {
          return successMessage;
        }.bind(this),
        function failure(response) {
          var message = response['data']['message'];

          if (response['status'] === 403) {
            var subject = response['data']['subject'];
            var huntId = stripAff4Prefix(subject).split('/')[1];

            this.grrAclDialogService_.openRequestHuntApprovalDialog(
                huntId, message);
          }
          return this.q_.reject(message);
        }.bind(this));
};

/**
 * Selects given item in the list.
 *
 * @param {!Object} item Item to be selected.
 * @export
 * @suppress {missingProperties} For items, as they crom from JSON response.
 */
HuntsListController.prototype.selectItem = function(item) {
  this.scope_['selectedHuntId'] = item.value.hunt_id.value;
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

  var modalInstance = this.uibModal_.open({
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
  var modalPromise = this.grrDialogService_.openConfirmation(
      'Run this hunt?',
      'Are you sure you want to run this hunt?',
      function() {
        var promise = this.grrApiService_.patch(this.buildHuntUrl_(),
                                                {state: 'STARTED'});
        return this.wrapApiPromise_(promise, 'Hunt started successfully!');
      }.bind(this));

  // TODO(user): there's no need to trigger update on dismiss.
  // Doing so only to maintain compatibility with legacy GRR code.
  // Remove as soon as legacy GRR code is removed.
  modalPromise.then(function resolve() {
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
  var modalPromise = this.grrDialogService_.openConfirmation(
      'Stop this hunt?',
      'Are you sure you want to stop this hunt? Once a hunt is ' +
          'stopped, resuming it is not possible.',
      function() {
        var promise = this.grrApiService_.patch(this.buildHuntUrl_(),
                                                {state: 'STOPPED'});
        return this.wrapApiPromise_(promise, 'Hunt stopped successfully!');
      }.bind(this));

  // TODO(user): there's no need to trigger update on dismiss.
  // Doing so only to maintain compatibility with legacy GRR code.
  // Remove as soon as legacy GRR code is removed.
  modalPromise.then(function resolve() {
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
  var components = this.scope_['selectedHuntId'].split('/');
  var huntId = components[components.length - 1];

  var argsObj = {};
  var modalPromise = this.grrDialogService_.openDirectiveDialog(
    'grrModifyHuntDialog', { huntId: huntId });

  // TODO(user): there's no need to trigger update on dismiss.
  // Doing so only to maintain compatibility with legacy GRR code.
  // Remove as soon as legacy GRR code is removed.
  modalPromise.then(function resolve() {
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
  modalScope.huntId = this.scope_['selectedHuntId'];
  modalScope.resolve = function() {
    modalInstance.close();
  };
  modalScope.reject = function() {
    modalInstance.dismiss();
  };

  this.scope_.$on('$destroy', function() {
    modalScope.$destroy();
  });

  var modalInstance = this.uibModal_.open({
    template: '<grr-new-hunt-wizard-copy-form on-resolve="resolve()" ' +
        'on-reject="reject()" hunt-id="huntId" />',
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
  var modalPromise = this.grrDialogService_.openConfirmation(
      'Delete this hunt?',
      'Are you sure you want to delete this hunt?',
      function() {
        var promise = this.grrApiService_.delete(this.buildHuntUrl_());
        return this.wrapApiPromise_(promise, 'Hunt deleted successfully!');
      }.bind(this));

  // TODO(user): there's no need to trigger update on dismiss.
  // Doing so only to maintain compatibility with legacy GRR code.
  // Remove as soon as legacy GRR code is removed.
  modalPromise.then(function resolve() {
    this.triggerUpdate();
  }.bind(this), function dismiss() {
    this.triggerUpdate();
  }.bind(this));
};


/**
 * Fills in huntsById dictionary.
 *
 * @param {!Array<Object>} items Items to be transformed.
 * @return {!Array<Object>} Transformed items.
 * @export
 * @suppress {missingProperties} For items, as they crom from JSON response.
 */
HuntsListController.prototype.transformItems = function(items) {
  angular.forEach(items, function(item) {
    this.huntsById[item['value']['hunt_id']['value']] = item;
  }.bind(this));

  return items;
};


/**
 * Displays a table with list of available hunts.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.HuntsListDirective = function() {
  return {
    scope: {
      selectedHuntId: '=?'
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
exports.HuntsListDirective.directive_name = 'grrHuntsList';
