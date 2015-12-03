'use strict';

goog.provide('grrUi.outputPlugins.outputPluginLogsDirective.OutputPluginLogsController');
goog.provide('grrUi.outputPlugins.outputPluginLogsDirective.OutputPluginLogsDirective');


goog.scope(function() {

/**
 * Controller for OutputPluginLogsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angularUi.$modal} $modal Bootstrap UI modal service.
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.outputPlugins.outputPluginLogsDirective.OutputPluginLogsController =
    function($scope, $modal, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angularUi.$modal} */
  this.modal_ = $modal;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {?number} */
  this.itemsCount;

  this.scope_.$watch('url', this.onUrlChange_.bind(this));
};
var OutputPluginLogsController =
    grrUi.outputPlugins.outputPluginLogsDirective.OutputPluginLogsController;


/**
 * Handles url changes.
 *
 * @param {string} newValue New url value.
 * @private
 */
OutputPluginLogsController.prototype.onUrlChange_ = function(newValue) {
  if (angular.isDefined(newValue)) {

    this.grrApiService_.get(newValue, {count: 1}).then(function(response) {
      this.itemsCount = response['data']['total_count'];
    }.bind(this));
  }
};


/**
 * Handles mouse clicks. Shows modal with collection items.
 *
 * @export
 */
OutputPluginLogsController.prototype.onClick = function() {
  this.modal_.open({
    templateUrl: '/static/angular-components/output-plugins/' +
        'output-plugin-logs-modal.html',
    scope: this.scope_,
    windowClass: 'wide-modal high-modal',
    size: 'lg'
  });
};


/**
 * Directive for displaying notes for output plugins of a flow or hunt.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.outputPlugins.outputPluginLogsDirective.OutputPluginLogsDirective =
    function() {
  return {
    scope: {
      url: '=',
      label: '@',
      cssClass: '@',
      icon: '@'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/output-plugins/' +
        'output-plugin-logs.html',
    controller: OutputPluginLogsController,
    controllerAs: 'controller'
  };
};

/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.outputPlugins.outputPluginLogsDirective.OutputPluginLogsDirective
    .directive_name = 'grrOutputPluginLogs';


});
