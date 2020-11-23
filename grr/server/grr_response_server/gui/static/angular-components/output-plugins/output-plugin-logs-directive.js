goog.module('grrUi.outputPlugins.outputPluginLogsDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');



/**
 * Controller for OutputPluginLogsDirective.
 * @unrestricted
 */
const OutputPluginLogsController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angularUi.$uibModal} $uibModal Bootstrap UI modal service.
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($scope, $uibModal, grrApiService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angularUi.$uibModal} */
    this.uibModal_ = $uibModal;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @type {?number} */
    this.itemsCount;

    this.scope_.$watch('url', this.onUrlChange_.bind(this));
  }

  /**
   * Handles url changes.
   *
   * @param {string} newValue New url value.
   * @private
   */
  onUrlChange_(newValue) {
    if (angular.isDefined(newValue)) {
      this.grrApiService_.get(newValue, {count: 1}).then(function(response) {
        this.itemsCount = response['data']['total_count'];
      }.bind(this));
    }
  }

  /**
   * Handles mouse clicks. Shows modal with collection items.
   *
   * @export
   */
  onClick() {
    this.uibModal_.open({
      templateUrl: '/static/angular-components/output-plugins/' +
          'output-plugin-logs-modal.html',
      scope: this.scope_,
      windowClass: 'wide-modal high-modal',
      size: 'lg'
    });
  }
};



/**
 * Directive for displaying notes for output plugins of a flow or hunt.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.OutputPluginLogsDirective = function() {
  return {
    scope: {url: '=', label: '@', cssClass: '@', icon: '@'},
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
exports.OutputPluginLogsDirective.directive_name = 'grrOutputPluginLogs';
