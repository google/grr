'use strict';

goog.provide('grrUi.config.binariesListDirective.BinariesListController');
goog.provide('grrUi.config.binariesListDirective.BinariesListDirective');
goog.provide('grrUi.config.binariesListDirective.sortBinaries');

goog.scope(function() {


grrUi.config.binariesListDirective.sortBinaries = function(binaries) {
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
var sortBinaries = grrUi.config.binariesListDirective.sortBinaries;


/**
 * Controller for BinariesListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.config.binariesListDirective.BinariesListController = function(
    $scope, grrApiService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Array<Object>|undefined} */
  this.binaries;

  this.scope_.$watchGroup(['binaries', 'binaryType'], this.onBinariesChange_.bind(this));
};
var BinariesListController =
    grrUi.config.binariesListDirective.BinariesListController;


BinariesListController.prototype.onBinariesChange_ = function() {
  this.binaries = [];
  if (angular.isDefined(this.scope_['binaries'])) {
    var filteredBinaries = this.scope_['binaries'].filter(function(b) {
      return b['value']['type']['value'] === this.scope_['typeFilter'];
    }.bind(this));
    this.binaries = sortBinaries(filteredBinaries);
  }
};

BinariesListController.prototype.onBinaryClicked = function(binary) {
  var url = '/config/binaries' + '/' + binary['value']['type']['value'] + '/' +
      binary['value']['path']['value'];
  this.grrApiService_.downloadFile(url);
};

/**
 * BinariesListDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.config.binariesListDirective.BinariesListDirective = function() {
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
grrUi.config.binariesListDirective.BinariesListDirective.directive_name =
    'grrBinariesList';

});  // goog.scope
