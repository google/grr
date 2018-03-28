'use strict';

goog.module('grrUi.config.binariesListDirective');
goog.module.declareLegacyNamespace();


/**
 * Sorts binaries by comparing path lengths.
 *
 * By "path length" we understand number of components in a path. For example,
 * path `foo/bar/baz` has length 3. In case of path with equal lengths, paths
 * are compared using the default (lexicographical) comparison.
 *
 * Note that returned array has some extra fields containing path information.
 *
 * @param {Array<Object>} binaries
 * @return {Array<Object>}
 */
exports.sortBinaries = function(binaries) {
  return binaries.map(function(b) {
    var newB = angular.copy(b);
    var pathComponents = newB['value']['path']['value'].split('/');
    newB['pathLen'] = pathComponents.length;
    newB['baseName'] = pathComponents.pop();
    newB['dirName'] = pathComponents.join('/');

    return newB;
  }).sort(function(a, b) {
    if (a['pathLen'] !== b['pathLen']) {
      return b['pathLen'] - a['pathLen'];
    }

    return a['value']['path']['value'].localeCompare(
        b['value']['path']['value']);
  });
};
var sortBinaries = exports.sortBinaries;


/**
 * Controller for BinariesListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const BinariesListController = function(
    $scope, grrApiService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Array<Object>|undefined} */
  this.binaries;

  this.scope_.$watchGroup(['binaries', 'binaryType'], this.onBinariesChange_.bind(this));
};


/**
 * @private
 */
BinariesListController.prototype.onBinariesChange_ = function() {
  this.binaries = [];
  if (angular.isDefined(this.scope_['binaries'])) {
    var filteredBinaries = this.scope_['binaries'].filter(function(b) {
      return b['value']['type']['value'] === this.scope_['typeFilter'];
    }.bind(this));
    this.binaries = sortBinaries(filteredBinaries);
  }
};

/**
 * Handler for binary list click action.
 *
 * @param {Object} binary
 */
BinariesListController.prototype.onBinaryClicked = function(binary) {
  var url = '/config/binaries-blobs/' + binary['value']['type']['value'] + '/' +
      binary['value']['path']['value'];
  this.grrApiService_.downloadFile(url);
};

/**
 * BinariesListDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.BinariesListDirective = function() {
  return {
    restrict: 'E',
    scope: {
      binaries: '=',
      typeFilter: '@'
    },
    templateUrl: '/static/angular-components/config/binaries-list.html',
    controller: BinariesListController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.BinariesListDirective.directive_name = 'grrBinariesList';
