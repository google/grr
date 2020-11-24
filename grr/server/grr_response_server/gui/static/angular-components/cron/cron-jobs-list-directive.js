goog.module('grrUi.cron.cronJobsListDirective');
goog.module.declareLegacyNamespace();

const aclDialogService = goog.requireType('grrUi.acl.aclDialogService');
const apiService = goog.requireType('grrUi.core.apiService');
const dialogService = goog.requireType('grrUi.core.dialogService');
const timeService = goog.requireType('grrUi.core.timeService');
const {stripAff4Prefix} = goog.require('grrUi.core.utils');



/**
 * Controller for CronJobsListDirective.
 * @unrestricted
 */
const CronJobsListController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angularUi.$uibModal} $uibModal Bootstrap UI modal service.
   * @param {!angular.$q} $q
   * @param {!timeService.TimeService} grrTimeService
   * @param {!apiService.ApiService} grrApiService
   * @param {!dialogService.DialogService} grrDialogService
   * @param {!aclDialogService.AclDialogService} grrAclDialogService
   * @ngInject
   */
  constructor(
      $scope, $uibModal, $q, grrTimeService, grrApiService, grrDialogService,
      grrAclDialogService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angularUi.$uibModal} */
    this.uibModal_ = $uibModal;

    /** @private {!angular.$q} */
    this.q_ = $q;

    /** @private {!timeService.TimeService} */
    this.timeService_ = grrTimeService;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {!dialogService.DialogService} */
    this.grrDialogService_ = grrDialogService;

    /** @private {!aclDialogService.AclDialogService} */
    this.grrAclDialogService_ = grrAclDialogService;

    /** @type {!Object<string, Object>} */
    this.cronJobsById = {};

    /** @type {string} */
    this.selectedCronJobId;

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
    this.scope_.$watch('controller.selectedCronJobId', function(newValue) {
      if (angular.isDefined(newValue)) {
        this.scope_['selectedCronJobId'] = newValue;
      }
    }.bind(this));

    // If outer binding changes, we want to update our selection.
    this.scope_.$watch('selectedCronJobId', function(newValue) {
      if (angular.isDefined(newValue)) {
        this.selectedCronJobId = newValue;
      }
    }.bind(this));
  }

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
  wrapApiPromise_(promise, successMessage) {
    return promise.then(
        function success() {
          return successMessage;
        }.bind(this),
        function failure(response) {
          var message = response['data']['message'];

          if (response['status'] === 403) {
            var subject = response['data']['subject'];
            var cronJobId = stripAff4Prefix(subject).split('/')[1];

            this.grrAclDialogService_.openRequestCronJobApprovalDialog(
                cronJobId, message);
          }
          return this.q_.reject(message);
        }.bind(this));
  }

  /**
   * Builds URL to get/patch/delete a cron job with a given ID.
   *
   * @param {string} cronJobId
   * @return {string} Corresponding URL.
   *
   * @private
   */
  buildCronJobUrl_(cronJobId) {
    return 'cron-jobs/' + cronJobId;
  }

  /**
   * Selects given item in the list.
   *
   * @param {!Object} item Item to be selected.
   * @export
   */
  selectItem(item) {
    this.selectedCronJobId = item['value']['cron_job_id']['value'];
  }

  /**
   * Transforms items fetched by API items provider so that they can be
   * correctly presented as cron tree.
   *
   * @param {!Array<Object>} items Items to be transformed.
   * @return {!Array<Object>} Transformed items.
   * @export
   */
  transformItems(items) {
    items = angular.copy(items);

    angular.forEach(items, function(item, index) {
      var cronJobId = item['value']['cron_job_id']['value'];
      this.cronJobsById[cronJobId] = item;

      var frequency = item['value']['frequency']['value'];
      var currentTime = this.timeService_.getCurrentTimeMs() / 1000;
      var last_run_time;
      if (angular.isDefined(item['value']['last_run_time'])) {
        last_run_time = item['value']['last_run_time']['value'] / 1000;
      } else {
        last_run_time = 0;
      }
      item.isStuck = (currentTime - last_run_time > frequency * 2);
    }.bind(this));

    return items;
  }

  /**
   * Shows new cron job wizard.
   *
   * @export
   */
  newCronJob() {
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
      this.selectedCronJobId =
          modalScope['result']['cronJob']['value']['cron_job_id']['value'];
    }.bind(this));
  }

  /**
   * Shows 'Enable Cron Job' confirmation dialog.
   *
   * @export
   */
  enableCronJob() {
    var modalPromise = this.grrDialogService_.openConfirmation(
        'Enable this cron job?',
        'Are you sure you want to ENABLE this cron job?', function() {
          var promise = this.grrApiService_.patch(
              this.buildCronJobUrl_(this.selectedCronJobId), {enabled: true});
          return this.wrapApiPromise_(
              promise, 'Cron job was ENABLED successfully!');
        }.bind(this));

    // TODO(user): there's no need to trigger update on dismiss.
    // Doing so only to maintain compatibility with legacy GRR code.
    // Remove as soon as legacy GRR code is removed.
    modalPromise.then(
        function resolve() {
          this.triggerUpdate();
        }.bind(this),
        function dismiss() {
          this.triggerUpdate();
        }.bind(this));
  }

  /**
   * Shows 'Disable Cron Job' confirmation dialog.
   *
   * @export
   */
  disableCronJob() {
    var modalPromise = this.grrDialogService_.openConfirmation(
        'Disable this cron job?',
        'Are you sure you want to DISABLE this cron job?', function() {
          var promise = this.grrApiService_.patch(
              this.buildCronJobUrl_(this.selectedCronJobId), {enabled: false});
          return this.wrapApiPromise_(
              promise, 'Cron job was DISABLED successfully!');
        }.bind(this));

    // TODO(user): there's no need to trigger update on dismiss.
    // Doing so only to maintain compatibility with legacy GRR code.
    // Remove as soon as legacy GRR code is removed.
    modalPromise.then(
        function resolve() {
          this.triggerUpdate();
        }.bind(this),
        function dismiss() {
          this.triggerUpdate();
        }.bind(this));
  }

  /**
   * Shows 'Delete Cron Job' confirmation dialog.
   *
   * @export
   */
  showDeleteCronJobConfirmation() {
    var dialogResult = this.grrDialogService_.openConfirmation(
        'Delete cron job', 'Are you sure you want to DELETE this cron job?',
        this.deleteCronJob_.bind(this));

    dialogResult.then(function resolve() {
      this.triggerUpdate();
    }.bind(this));
  }

  /**
   * Deletes the selected cron job.
   *
   * @return {!angular.$q.Promise} A promise indicating success or failure.
   * @private
   */
  deleteCronJob_() {
    var url = this.buildCronJobUrl_(this.selectedCronJobId);
    var promise = this.grrApiService_.delete(url);
    return this.wrapApiPromise_(promise, 'Cron job was deleted successfully!');
  }

  /**
   * Shows 'Force Run Cron Job' confirmation dialog.
   *
   * @export
   */
  forceRunCronJob() {
    var modalPromise = this.grrDialogService_.openConfirmation(
        'Force-run this cron job?',
        'Are you sure you want to FORCE-RUN this cron job?', function() {
          var promise = this.grrApiService_.post(
              this.buildCronJobUrl_(this.selectedCronJobId) +
              '/actions/force-run');
          return this.wrapApiPromise_(
              promise, 'Cron job flow was FORCE-STARTED successfully!');
        }.bind(this));

    // TODO(user): there's no need to trigger update on dismiss.
    // Doing so only to maintain compatibility with legacy GRR code.
    // Remove as soon as legacy GRR code is removed.
    modalPromise.then(
        function resolve() {
          this.triggerUpdate();
        }.bind(this),
        function dismiss() {
          this.triggerUpdate();
        }.bind(this));
  }
};


/**
 * Cron jobs list API url.
 * @const {string}
 */
CronJobsListController.prototype.cronUrl = '/cron-jobs';



/**
 * CronJobsListDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
exports.CronJobsListDirective = function() {
  return {
    scope: {
      selectedCronJobId: '=?',
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
exports.CronJobsListDirective.directive_name = 'grrCronJobsList';
