'use strict';

goog.provide('grrUi.hunt.huntsListDirective.HuntsListController');
goog.provide('grrUi.hunt.huntsListDirective.HuntsListDirective');

goog.require('grrUi.core.utils.stripAff4Prefix');

goog.scope(function() {



/**
 * Controller for HuntsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$q} $q
 * @param {!angularUi.$uibModal} $uibModal Bootstrap UI modal service.
 * @param {grrUi.core.dialogService.DialogService} grrDialogService
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.acl.aclDialogService.AclDialogService} grrAclDialogService
 * @ngInject
 */
grrUi.hunt.huntsListDirective.HuntsListController = function(
    $scope, $q, $uibModal, grrDialogService, grrApiService,
    grrAclDialogService) {
  // Injected dependencies.

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!angularUi.$uibModal} */
  this.uibModal_ = $uibModal;

  /** @private {grrUi.core.dialogService.DialogService} */
  this.grrDialogService_ = grrDialogService;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.acl.aclDialogService.AclDialogService} */
  this.grrAclDialogService_ = grrAclDialogService;

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


HuntsListController.prototype.buildHuntUrl_ = function() {
  var components = this.scope_['selectedHuntUrn'].split('/');
  var basename = components[components.length - 1];
  return this.huntsUrl + '/' + basename;
};

HuntsListController.prototype.wrapApiPromise_ = function(promise, successMessage) {
    return promise.then(
        function success() {
          return successMessage;
        }.bind(this),
        function failure(response) {
          var message = response['data']['message'];

          if (response['status'] === 403) {
            var subject = response['data']['subject'];
            var huntId = grrUi.core.utils.stripAff4Prefix(
                subject).split('/')[1];

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
  var components = this.scope_['selectedHuntUrn'].split('/');
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

  var modalInstance = this.uibModal_.open({
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
