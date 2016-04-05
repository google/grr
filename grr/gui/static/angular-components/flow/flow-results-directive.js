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

  /**
   * Flow urn is expected to look like:
   * [aff4:/]C.0000111122223333/flows/F:ABC123
   */
  var components = newValue.split('/');
  if (components.length == 0) {
    throw new Error('Client\'s flow URN was empty.');
  }

  if (components[0] == 'aff4:') {
    components = components.slice(1);
  }
  if (components.length < 3 || components[1] != 'flows') {
    throw new Error('Unexpected client\'s flow URN structure: ' + newValue);
  }

  var clientId = components[0];
  var flowId = components[2];

  this.flowResultsUrl = '/clients/' + clientId + '/flows/' + flowId +
      '/results';
  this.outputPluginsUrl = '/clients/' + clientId + '/flows/' +
      flowId + '/output-plugins';
  this.exportCommandUrl = this.flowResultsUrl + '/export-command';
  this.downloadFilesUrl = this.flowResultsUrl + '/files-archive';
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
