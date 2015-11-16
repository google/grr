'use strict';

goog.provide('grrUi.core.aff4DownloadLinkDirective.Aff4DownloadLinkController');
goog.provide('grrUi.core.aff4DownloadLinkDirective.Aff4DownloadLinkDirective');


goog.scope(function() {


/**
 * Controller for Aff4DownloadLinkDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!angular.$cookies} $cookies
 * @ngInject
 */
grrUi.core.aff4DownloadLinkDirective.Aff4DownloadLinkController = function(
    $scope, $element, $cookies) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!angular.$cookies} */
  this.cookies_ = $cookies;

  /** @export {string} */
  this.reason = grr.state.reason;

  /** @export {string|undefined} */
  this.csrfToken = $cookies.get('csrftoken');
};
var Aff4DownloadLinkController =
    grrUi.core.aff4DownloadLinkDirective.Aff4DownloadLinkController;


/**
 * Handles clicks on the download link.
 *
 * @export
 */
Aff4DownloadLinkController.prototype.onClick = function() {
  var form = this.element_.find('form');
  form.submit();
};

/**
 * Directive for download links to aff4 streams.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.aff4DownloadLinkDirective.Aff4DownloadLinkDirective =
    function() {
  return {
    scope: {
      aff4Path: '=',
      safeExtension: '='
    },
    transclude: true,
    restrict: 'E',
    templateUrl: '/static/angular-components/core/aff4-download-link.html',
    controller: Aff4DownloadLinkController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.core.aff4DownloadLinkDirective.Aff4DownloadLinkDirective
    .directive_name = 'grrAff4DownloadLink';


});  // goog.scope
