'use strict';

goog.provide('grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnController');
goog.provide('grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnDirective');

goog.require('grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective');


goog.scope(function() {


var ERROR_EVENT_NAME = grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective.error_event_name;


/**
 * Controller for DownloadableUrnDirective.
 *
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnController =
    function($rootScope, $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;
};

var DownloadableUrnController =
    grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnController;


DownloadableUrnController.prototype.onDownloadClick = function() {
  this.grrApiService_.downloadFile(
      this.scope_['value']['downloadUrl'],
      this.scope_['value']['downloadParams']).then(
          function success() {}.bind(this),
          function failure(response) {
            if (response.status !== 500) {
              this.rootScope_.$broadcast(
                  ERROR_EVENT_NAME, {
                    message: 'Couldn\'t download the file. Most likely ' +
                        'it was just referenced and not downloaded from the ' +
                        'client.'
                  });
            }
          }.bind(this));
};


/**
 * Directive that displays DownloadableUrn values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnDirective =
    function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/pseudo/' +
        'downloadable-urn.html',
    controller: DownloadableUrnController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnDirective
    .directive_name = 'grrDownloadableUrn';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnDirective
    .semantic_type = '__DownloadableUrn';


});  // goog.scope
