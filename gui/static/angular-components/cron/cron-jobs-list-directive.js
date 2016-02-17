'use strict';

goog.provide('grrUi.cron.cronJobsListDirective.CronJobsListController');
goog.provide('grrUi.cron.cronJobsListDirective.CronJobsListDirective');

goog.scope(function() {

/** @const {string} */
grrUi.cron.cronJobsListDirective.
    USE_OO_HUNT_RULES_IN_NEW_CRON_JOB_WIZARD_URL = '/config/AdminUI.' +
    'new_hunt_wizard.use_oo_hunt_rules_in_new_cron_job_wizard';
var USE_OO_HUNT_RULES_IN_NEW_CRON_JOB_WIZARD_URL =
    grrUi.cron.cronJobsListDirective.
    USE_OO_HUNT_RULES_IN_NEW_CRON_JOB_WIZARD_URL;

/**
 * Controller for CronJobsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angularUi.$modal} $modal Bootstrap UI modal service.
 * @param {!grrUi.core.timeService.TimeService} grrTimeService
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.cron.cronJobsListDirective.CronJobsListController = function(
    $scope, $modal, grrTimeService, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angularUi.$modal} */
  this.modal_ = $modal;

  /** @private {!grrUi.core.timeService.TimeService} */
  this.timeService_ = grrTimeService;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {!Object<string, Object>} */
  this.cronJobsByUrn = {};

  /** @type {string|undefined} */
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

  this.grrApiService_.get(USE_OO_HUNT_RULES_IN_NEW_CRON_JOB_WIZARD_URL).
      then(function(response) {
    this.ooCronHuntsEnabled = response['data']['value']['value'];
    if (angular.isString(this.ooCronHuntsEnabled)) {
      throw new Error('Got a string where boolean/integer was expected.');
    }
    this.ooCronHuntsEnabled = Boolean(this.ooCronHuntsEnabled);
  }.bind(this));

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

  var tagName = 'grr-new-cron-job-' +
      (this.ooCronHuntsEnabled ? '' : 'deprecated-') + 'wizard-form';

  var modalInstance = this.modal_.open({
    template: '<' + tagName + ' on-resolve="resolve()" ' +
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
  var modalInstance = this.modal_.open({
    template: '<grr-legacy-renderer ' +
        'renderer="EnableCronJobConfirmationDialog" ' +
        'query-params="{cron_urn: controller.selectedCronJobUrn}" />',
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
 * Shows 'Disable Cron Job' confirmation dialog.
 *
 * @export
 */
CronJobsListController.prototype.disableCronJob = function() {
  var modalInstance = this.modal_.open({
    template: '<grr-legacy-renderer ' +
        'renderer="DisableCronJobConfirmationDialog" ' +
        'query-params="{cron_urn: controller.selectedCronJobUrn}" />',
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
 * Shows 'Delete Cron Job' confirmation dialog.
 *
 * @export
 */
CronJobsListController.prototype.deleteCronJob = function() {
  var modalInstance = this.modal_.open({
    template: '<grr-legacy-renderer ' +
        'renderer="DeleteCronJobConfirmationDialog" ' +
        'query-params="{cron_urn: controller.selectedCronJobUrn}" />',
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
 * Shows 'Force Run Cron Job' confirmation dialog.
 *
 * @export
 */
CronJobsListController.prototype.forceRunCronJob = function() {
  var modalInstance = this.modal_.open({
    template: '<grr-legacy-renderer ' +
        'renderer="ForceRunCronJobConfirmationDialog" ' +
        'query-params="{cron_urn: controller.selectedCronJobUrn}" />',
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
