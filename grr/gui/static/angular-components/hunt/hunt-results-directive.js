'use strict';

goog.provide('grrUi.hunt.huntResultsDirective.HuntResultsController');
goog.provide('grrUi.hunt.huntResultsDirective.HuntResultsDirective');

goog.require('grrUi.core.fileDownloadUtils.getFileUrnFromValue');
goog.require('grrUi.core.fileDownloadUtils.makeValueDownloadable');

goog.scope(function() {



/**
 * Controller for HuntResultsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.hunt.huntResultsDirective.HuntResultsController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @export {string} */
  this.resultsUrl;

  /** @export {string} */
  this.outputPluginsUrl;

  /** @export {string} */
  this.downloadFilesUrl;

  $scope.$watch('huntUrn', this.onHuntUrnChange.bind(this));
};
var HuntResultsController =
    grrUi.hunt.huntResultsDirective.HuntResultsController;


/**
 * Handles huntUrn attribute changes.
 *
 * @param {?string} huntUrn
 * @export
 */
HuntResultsController.prototype.onHuntUrnChange = function(huntUrn) {
  if (!angular.isString(huntUrn)) {
    return;
  }

  var components = huntUrn.split('/');
  var huntId = components[components.length - 1];

  this.resultsUrl = '/hunts/' + huntId + '/results';
  this.downloadFilesUrl = this.resultsUrl + '/files-archive';
  this.outputPluginsUrl = '/hunts/' + huntId + '/output-plugins';
};


/**
 * Transforms hunt results so that if they're pointing to files, corresponding
 * RDFURNs will be changed to __DownloadableUrn with a proper url set.
 *
 * @param {Array<Object>} items
 * @return {Array<Object>}
 * @export
 */
HuntResultsController.prototype.transformItems = function(items) {
  var components = this.scope_['huntUrn'].split('/');
  var huntId = components[components.length - 1];
  var urlPrefix = '/hunts/' + huntId + '/results/clients';
  var aff4Prefix = 'aff4:/';

  var newItems = items.map(function(item) {
    var aff4Path = grrUi.core.fileDownloadUtils.getFileUrnFromValue(item);
    if (!aff4Path) {
      return item;
    }

    if (aff4Path.toLowerCase().indexOf(aff4Prefix) == 0) {
      aff4Path = aff4Path.substr(aff4Prefix.length);
    }
    var components = aff4Path.split('/');
    var clientId = components[0];
    var vfsPath = components.slice(1).join('/');
    if (vfsPath.indexOf('fs/') === 0) {
      vfsPath = vfsPath.substr(3);
    } else {
      return item;
    }

    var downloadUrl = urlPrefix + '/' + clientId + '/fs/' + vfsPath;
    var downloadParams = {'timestamp': item['value']['timestamp']['value']};

    var downloadableItem = angular.copy(item);
    grrUi.core.fileDownloadUtils.makeValueDownloadable(
        downloadableItem, downloadUrl, downloadParams);

    return downloadableItem;
  });

  return newItems;
};


/**
 * Directive for displaying results of a hunt with a given URN.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.huntResultsDirective.HuntResultsDirective = function() {
  return {
    scope: {
      huntUrn: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-results.html',
    controller: HuntResultsController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.huntResultsDirective.HuntResultsDirective.directive_name =
    'grrHuntResults';

});  // goog.scope
