'use strict';

goog.provide('grrUi.semantic.clientUrnDirective.ClientUrnDirective');

goog.scope(function() {



/**
 * Controller for the ClientUrnDirective.
 *
 * @param {!angular.Scope} $scope Directive's scope.
 * @param {!angularUi.$modal} $modal Bootstrap UI modal service.
 * @param {!grrUi.core.apiService.ApiService} grrApiService GRR Aff4 service.
 * @constructor
 * @ngInject
 */
var ClientUrnController = function(
    $scope, $modal, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?} */
  this.scope_.value;

  /** @private {!angularUi.$modal} */
  this.modal_ = $modal;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object} */
  this.clientDetails;

  /** @export {?string} */
  this.clientUrn;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};


/**
 * Handles value changes.
 *
 * @export
 */
ClientUrnController.prototype.onValueChange = function() {
  if (angular.isObject(this.scope_.value)) {
    this.clientUrn = this.scope_.value.value;
  } else {
    this.clientUrn = this.scope_.value;
  }
};


/**
 * Shows a modal with information about the client. Called when "info"
 * button is clicked.
 *
 * @export
 */
ClientUrnController.prototype.onInfoClick = function() {
  this.modal_.open({
    templateUrl: '/static/angular-components/semantic/client-urn-modal.html',
    scope: this.scope_
  });

  var clientId = this.clientUrn.split('/')[1];
  this.grrApiService_.get('clients/' + clientId).then(
      function(response) {
        this.clientDetails = response.data.client;
      }.bind(this));
};


/**
 * Called when the link is clicked. Opens corresponding client.
 *
 * @export
 */
ClientUrnController.prototype.onLinkClick = function() {
  var hash = $.param({
    'main': 'HostInformation',
    'c': this.clientUrn
  });
  grr.loadFromHash(hash);
};


/**
 * Directive that displays given client URN as a link. Clicking on the link
 * opens corresponding client. There's also a little "info" button next to
 * the link that opens a modal with information about the client.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.semantic.clientUrnDirective.ClientUrnDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/client-urn.html',
    controller: ClientUrnController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.clientUrnDirective.ClientUrnDirective.directive_name =
    'grrClientUrn';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.clientUrnDirective.ClientUrnDirective.semantic_type =
    'ClientURN';


});  // goog.scope
