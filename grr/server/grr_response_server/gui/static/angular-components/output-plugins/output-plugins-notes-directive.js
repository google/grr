goog.module('grrUi.outputPlugins.outputPluginsNotesDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');



/**
 * Controller for OutputPluginsNotesDirective.
 * @unrestricted
 */
const OutputPluginsNotesController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($scope, grrApiService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @export {?string} */
    this.error;

    /** @export {Array<Object>} */
    this.outputPlugins;

    this.scope_.$watch(
        'outputPluginsUrl', this.onOutputPluginsUrlChange_.bind(this));
  }

  /**
   * Handles changes in metadata url.
   *
   * @param {?string} newValue New metadata url.
   * @private
   */
  onOutputPluginsUrlChange_(newValue) {
    if (angular.isDefined(newValue)) {
      this.grrApiService_.get(/** @type {string} */ (newValue))
          .then(
              function success(response) {
                this.outputPlugins = response['data']['items'];
              }.bind(this),
              function failure(response) {
                this.error = response['data']['message'];
              }.bind(this));
    }
  }
};



/**
 * Directive for displaying notes for output plugins of a flow or hunt.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.OutputPluginsNotesDirective = function() {
  return {
    scope: {outputPluginsUrl: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/output-plugins/' +
        'output-plugins-notes.html',
    controller: OutputPluginsNotesController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.OutputPluginsNotesDirective.directive_name = 'grrOutputPluginsNotes';
