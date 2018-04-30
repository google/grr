'use strict';

goog.module('grrUi.flow.flowResultsDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for FlowResultsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const FlowResultsController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?string} */
  this.flowResultsUrl;

  /** @type {?string} */
  this.flowExportedResultsUrl;

  /** @type {?string} */
  this.outputPluginsMetadataUrl;

  /** @type {?string} */
  this.downloadFilesUrl;

  /** @type {?string} */
  this.exportCommand;

  this.scope_.$watchGroup(['flowId', 'apiBasePath'],
                          this.onFlowIdOrBasePathChange_.bind(this));
};


/**
 * Handles directive's arguments changes.
 *
 * @param {Array<string>} newValues
 * @private
 */
FlowResultsController.prototype.onFlowIdOrBasePathChange_ = function(
    newValues) {
  this.flowResultsUrl = this.outputPluginsMetadataUrl =
      this.downloadFilesUrl = null;

  if (newValues.every(angular.isDefined)) {
    var flowUrl = this.scope_['apiBasePath'] + '/' + this.scope_['flowId'];
    this.flowResultsUrl = flowUrl + '/results';
    this.flowExportedResultsUrl = flowUrl + '/exported-results';
    this.outputPluginsUrl = flowUrl + '/output-plugins';
    this.exportCommandUrl = flowUrl + '/results/export-command';
    this.downloadFilesUrl = flowUrl + '/results/files-archive';
  }
};


/**
 * Directive for displaying results of a flow with a given URL.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.FlowResultsDirective = function() {
  return {
    scope: {
      flowId: '=',
      apiBasePath: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-results.html',
    controller: FlowResultsController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.FlowResultsDirective.directive_name = 'grrFlowResults';
