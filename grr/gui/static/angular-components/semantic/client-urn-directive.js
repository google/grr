'use strict';

goog.module('grrUi.semantic.clientUrnDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for the ClientUrnDirective.
 *
 * @param {!angular.Scope} $scope Directive's scope.
 * @param {!angularUi.$uibModal} $uibModal Bootstrap UI modal service.
 * @param {!grrUi.core.apiService.ApiService} grrApiService GRR Aff4 service.
 * @constructor
 * @ngInject
 */
var ClientUrnController = function($scope, $uibModal, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?} */
  this.scope_.value;

  /** @private {!angularUi.$uibModal} */
  this.uibModal_ = $uibModal;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object} */
  this.clientDetails;

  /** @private {?string} */
  this.clientId;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};


/**
 * Handles value changes.
 *
 * @export
 */
ClientUrnController.prototype.onValueChange = function() {
  var clientUrn;
  if (angular.isObject(this.scope_.value)) {
    clientUrn = this.scope_.value.value;
  } else {
    clientUrn = this.scope_.value;
  }

  if (angular.isString(clientUrn)) {
    this.clientId = clientUrn.replace(/^aff4:\//, '');
  }
};


/**
 * Shows a modal with information about the client. Called when "info"
 * button is clicked.
 *
 * @export
 */
ClientUrnController.prototype.onInfoClick = function() {
  this.uibModal_.open({
    templateUrl: '/static/angular-components/semantic/client-urn-modal.html',
    scope: this.scope_
  });

  this.grrApiService_.get('clients/' + this.clientId).then(
      function(response) {
        this.clientDetails = response.data;
      }.bind(this));
};


/**
 * Directive that displays given client URN as a link. Clicking on the link
 * opens corresponding client. There's also a little "info" button next to
 * the link that opens a modal with information about the client.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.ClientUrnDirective = function() {
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
exports.ClientUrnDirective.directive_name = 'grrClientUrn';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.ClientUrnDirective.semantic_types = ['ClientURN', 'ApiClientId'];
