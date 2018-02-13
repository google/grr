'use strict';

goog.module('grrUi.outputPlugins.outputPluginsNotesDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for OutputPluginsNotesDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const OutputPluginsNotesController =
    function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {?string} */
  this.error;

  /** @export {Array<Object>} */
  this.outputPlugins;

  this.scope_.$watch('outputPluginsUrl',
                     this.onOutputPluginsUrlChange_.bind(this));
};


/**
 * Handles changes in metadata url.
 *
 * @param {?string} newValue New metadata url.
 * @private
 */
OutputPluginsNotesController.prototype.onOutputPluginsUrlChange_ = function(
    newValue) {
  if (angular.isDefined(newValue)) {
    this.grrApiService_.get(/** @type {string} */ (newValue)).then(
        function success(response) {
          this.outputPlugins = response['data']['items'];
        }.bind(this),
        function failure(response) {
          this.error = response['data']['message'];
        }.bind(this));
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
    scope: {
      outputPluginsUrl: '='
    },
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
