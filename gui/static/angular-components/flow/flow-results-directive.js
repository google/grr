'use strict';

goog.provide('grrUi.flow.flowResultsDirective.FlowResultsController');
goog.provide('grrUi.flow.flowResultsDirective.FlowResultsDirective');
goog.require('grrUi.core.downloadCollectionFilesDirective.valuePointsToFile');

goog.scope(function() {



/**
 * Controller for FlowResultsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.flow.flowResultsDirective.FlowResultsController = function($scope) {
  /** @type {string} */
  this.flowResultsUrl;

  /** @type {string} */
  this.outputPluginsMetadataUrl;

  /** @type {string} */
  this.downloadFilesUrl;

  /** @type {string} */
  this.exportCommand;

  $scope.$watch('flowUrn', this.onFlowUrnChange.bind(this));
};
var FlowResultsController =
    grrUi.flow.flowResultsDirective.FlowResultsController;


/**
 * Handles flowUrn attribute changes.
 *
 * @param {string} newValue
 * @export
 */
FlowResultsController.prototype.onFlowUrnChange = function(newValue) {
  this.flowResultsUrl = this.outputPluginsMetadataUrl =
      this.downloadFilesUrl = '';

  if (!angular.isString(newValue)) {
    return;
  }

  var components = newValue.split('/');
  if (components.length == 0) {
    return;
  }

  if (components[0] == 'aff4:') {
    components = components.slice(1);
  }
  if (components.length < 3) {
    return;
  }

  var clientId = components[0];
  var flowId = components[2];

  this.flowResultsUrl = '/clients/' + clientId + '/flows/' + flowId +
      '/results';
  this.outputPluginsMetadataUrl = '/clients/' + clientId + '/flows/' +
      flowId + '/output-plugins';
  this.exportCommandUrl = this.flowResultsUrl + '/export-command';
  this.downloadFilesUrl = this.flowResultsUrl + '/archive-files';
};


/**
 * Directive for displaying results of a flow with a given URN.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.flow.flowResultsDirective.FlowResultsDirective = function() {
  return {
    scope: {
      flowUrn: '='
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
grrUi.flow.flowResultsDirective.FlowResultsDirective.directive_name =
    'grrFlowResults';


});  // goog.scope
