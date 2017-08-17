'use strict';

goog.provide('grrUi.cron.cronJobsListDirective.CronJobsListController');
goog.provide('grrUi.cron.cronJobsListDirective.CronJobsListDirective');

goog.require('grrUi.core.utils.stripAff4Prefix');

goog.scope(function() {


/**
 * Controller for CronJobsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angularUi.$uibModal} $uibModal Bootstrap UI modal service.
 * @param {!angular.$q} $q
 * @param {!grrUi.core.timeService.TimeService} grrTimeService
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.core.dialogService.DialogService} grrDialogService
 * @param {!grrUi.acl.aclDialogService.AclDialogService} grrAclDialogService
 * @ngInject
 */
grrUi.cron.cronJobsListDirective.CronJobsListController = function(
    $scope, $uibModal, $q, grrTimeService, grrApiService, grrDialogService,
    grrAclDialogService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angularUi.$uibModal} */
  this.uibModal_ = $uibModal;

  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!grrUi.core.timeService.TimeService} */
  this.timeService_ = grrTimeService;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.core.dialogService.DialogService} */
  this.grrDialogService_ = grrDialogService;

  /** @private {!grrUi.acl.aclDialogService.AclDialogService} */
  this.grrAclDialogService_ = grrAclDialogService;

  /** @type {!Object<string, Object>} */
  this.cronJobsByUrn = {};

  /** @type {string} */
  this.selectedCronJobUrn;

  /**
   * This variable is bound to grr-infinite-table's trigger-update attribute
   * and therefore is set by that directive to a function that triggers
   * table update.
   * @export {function()}
   */
  this.triggerUpdate;

  /** {private} */
  this.ooCronHuntsEnabled;

  // Push the selection changes back to the scope, so that other UI components
  // can react on the change.
  this.scope_.$watch('controller.selectedCronJobUrn', function(newValue) {
    if (angular.isDefined(newValue)) {
      this.scope_['selectedCronJobUrn'] = newValue;
    }
  }.bind(this));

  // If outer binding changes, we want to update our selection.
  this.scope_.$watch('selectedCronJobUrn', function(newValue) {
    if (angular.isDefined(newValue)) {
      this.selectedCronJobUrn = newValue;
    }
  }.bind(this));
};
var CronJobsListController =
    grrUi.cron.cronJobsListDirective.CronJobsListController;


/**
 * Cron jobs list API url.
 * @const {string}
 */
CronJobsListController.prototype.cronUrl = '/cron-jobs';


/**
 * Wraps a given API service promise, so that if "forbidden" response is
 * received, grrAclDialogService is used to show  'Request an approval' dialog
 * box.
 *
 * @param {!angular.$q.Promise} promise
 * @param {string} successMessage Message to return on success.
 * @return {!angular.$q.Promise} Wrapped promise.
 *
 * @private
 */
CronJobsListController.prototype.wrapApiPromise_ = function(
    promise, successMessage) {
    return promise.then(
        function success() {
          return successMessage;
        }.bind(this),
        function failure(response) {
          var message = response['data']['message'];

          if (response['status'] === 403) {
            var subject = response['data']['subject'];
            var cronJobId = grrUi.core.utils.stripAff4Prefix(
                subject).split('/')[1];

            this.grrAclDialogService_.openRequestCronJobApprovalDialog(
                cronJobId, message);
          }
          return this.q_.reject(message);
        }.bind(this));
};


/**
 * Builds URL to get/patch/delete a cron job with a given URN.
 *
 * @param {string} cronJobUrn
 * @return {string} Corresponding URL.
 *
 * @private
 */
CronJobsListController.prototype.buildCronJobUrl_ = function(cronJobUrn) {
  var cronJobId = cronJobUrn.split('/')[2];
  return 'cron-jobs/' + cronJobId;
};


/**
 * Selects given item in the list.
 *
 * @param {!Object} item Item to be selected.
 * @export
 */
CronJobsListController.prototype.selectItem = function(item) {
  this.selectedCronJobUrn = item['value']['urn']['value'];
};


/**
 * Transforms items fetched by API items provider so that they can be
 * correctly presented as cron tree.
 *
 * @param {!Array<Object>} items Items to be transformed.
 * @return {!Array<Object>} Transformed items.
 * @export
 */
CronJobsListController.prototype.transformItems = function(items) {
  items = angular.copy(items);

  angular.forEach(items, function(item, index) {
    var urn = item['value']['urn']['value'];
    this.cronJobsByUrn[urn] = item;

    var components = urn.split('/');
    item.shortUrn = components[components.length - 1];

    var periodicity = item['value']['periodicity']['value'];
    var currentTime = this.timeService_.getCurrentTimeMs() / 1000;
    var last_run_time;
    if (angular.isDefined(item['value']['last_run_time'])) {
        last_run_time = item['value']['last_run_time']['value'] / 1000;
    } else {
      last_run_time = 0;
    }
    item.isStuck = (currentTime - last_run_time > periodicity * 2);
  }.bind(this));

  return items;
};


/**
 * Shows new cron job wizard.
 *
 * @export
 */
CronJobsListController.prototype.newCronJob = function() {
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
  modalScope.result = {};

  var modalInstance = this.uibModal_.open({
    template: '<grr-new-cron-job-wizard-form on-resolve="resolve()" ' +
        'on-reject="reject()" cron-job="result.cronJob" />',
    scope: modalScope,
    windowClass: 'wide-modal high-modal',
    size: 'lg'
  });

  modalInstance.result.then(function resolve() {
    this.triggerUpdate();
    this.selectedCronJobUrn =
        modalScope['result']['cronJob']['value']['urn']['value'];
  }.bind(this));
};


/**
 * Shows 'Enable Cron Job' confirmation dialog.
 *
 * @export
 */
CronJobsListController.prototype.enableCronJob = function() {
  var modalPromise = this.grrDialogService_.openConfirmation(
      'Enable this cron job?',
      'Are you sure you want to ENABLE this cron job?',
      function() {
        var promise = this.grrApiService_.patch(
            this.buildCronJobUrl_(this.selectedCronJobUrn),
            {state: 'ENABLED'});
        return this.wrapApiPromise_(promise,
                                    'Cron job was ENABLED successfully!');
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
 * Shows 'Disable Cron Job' confirmation dialog.
 *
 * @export
 */
CronJobsListController.prototype.disableCronJob = function() {
  var modalPromise = this.grrDialogService_.openConfirmation(
      'Disable this cron job?',
      'Are you sure you want to DISABLE this cron job?',
      function() {
        var promise = this.grrApiService_.patch(
            this.buildCronJobUrl_(this.selectedCronJobUrn),
            {state: 'DISABLED'});
        return this.wrapApiPromise_(promise,
                                    'Cron job was DISABLED successfully!');
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
 * Shows 'Delete Cron Job' confirmation dialog.
 *
 * @export
 */
CronJobsListController.prototype.showDeleteCronJobConfirmation = function() {
  var dialogResult = this.grrDialogService_.openConfirmation(
      'Delete cron job', 'Are you sure you want to DELETE this cron job?',
      this.deleteCronJob_.bind(this));

  dialogResult.then(function resolve() {
    this.triggerUpdate();
  }.bind(this));
};

/**
 * Deletes the selected cron job.
 *
 * @return {!angular.$q.Promise} A promise indicating success or failure.
 * @private
 */
CronJobsListController.prototype.deleteCronJob_ = function() {
  var url = this.buildCronJobUrl_(this.selectedCronJobUrn);
  var deferred = this.q_.defer();

  this.grrApiService_.delete(url).then(
    function success(){
      deferred.resolve('Cron job was deleted successfully!');
    },
    function failure(response) {
      if (response.status === 403) {
        var headers = response.headers();
        this.grrAclDialogService_.openRequestCronJobApprovalDialog(
            headers['x-grr-unauthorized-access-subject'],
            headers['x-grr-unauthorized-access-reason']);
      } else {
        deferred.reject(response.data.message);
      }
    }.bind(this));

  return deferred.promise;
};

/**
 * Shows 'Force Run Cron Job' confirmation dialog.
 *
 * @export
 */
CronJobsListController.prototype.forceRunCronJob = function() {
  var modalPromise = this.grrDialogService_.openConfirmation(
      'Force-run this cron job?',
      'Are you sure you want to FORCE-RUN this cron job?',
      function() {
        var promise = this.grrApiService_.post(
            this.buildCronJobUrl_(this.selectedCronJobUrn) +
                '/actions/force-run');
        return this.wrapApiPromise_(
            promise,
            'Cron job flow was FORCE-STARTED successfully!');
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
 * CronJobsListDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.cron.cronJobsListDirective.CronJobsListDirective = function() {
  return {
    scope: {
      selectedCronJobUrn: '=?',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/cron-jobs-list.html',
    controller: CronJobsListController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.cron.cronJobsListDirective.CronJobsListDirective
    .directive_name = 'grrCronJobsList';



});  // goog.scope
