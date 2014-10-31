'use strict';

goog.provide('grrUi.semantic.clientUrnDirective.ClientUrnDirective');

goog.scope(function() {



/**
 * Controller for the ClientUrnDirective.
 *
 * @param {!angular.Scope} $scope Directive's scope.
 * @param {!angular.Element} $element Element this directive operates on.
 * @param {!Object} $modal Bootstrap UI modal service.
 * @param {!grrUi.core.Aff4Service} grrAff4Service GRR Aff4 service.
 * @constructor
 * @ngInject
 */
var ClientUrnDirectiveController = function(
    $scope, $element, $modal, grrAff4Service) {
  this.scope = $scope;
  this.element = $element;
  this.modal = $modal;
  this.grrAff4Service = grrAff4Service;

  this.scope.client = {
    summary: null
  };
};


/**
 * Called when "info" button is clicked. Shows a modal with information
 * about the client.
 */
ClientUrnDirectiveController.prototype.onInfoClick = function() {
  this.scope.client.summary = null;

  var modalInstance = this.modal.open({
    templateUrl: 'static/angular-components/semantic/client-urn-modal.html',
    scope: this.scope
  });

  var scope = this.scope;
  this.grrAff4Service.get(this.scope.value, {
    'with_type_info': true,
    'with_descriptors': true}).then(function(response) {
    scope.client.summary = response.data.summary;
  });
};


/**
 * Called when the link is clicked. Opens corresponding client.
 */
ClientUrnDirectiveController.prototype.onLinkClick = function() {
  var hash = $.param({'main': 'HostInformation',
    'c': this.scope.value});
  grr.loadFromHash(hash);
};



/**
 * Directive that displays given client URN as a link. Clicking on the link
 * opens corresponding client. There's also a little "info" button next to
 * the link that opens a modal with information about the client.
 *
 * @constructor
 * @param {grrUi.core.aff4Service.Aff4Service} grrAff4Service
 * @ngInject
 * @export
 */
grrUi.semantic.clientUrnDirective.ClientUrnDirective = function(
    grrAff4Service) {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: 'static/angular-components/semantic/client-urn.html',
    controller: ClientUrnDirectiveController,
    controllerAs: 'ctrl'
  };
};


/**
 * Name of the directive in Angular.
 */
grrUi.semantic.clientUrnDirective.ClientUrnDirective.directive_name =
    'grrClientUrn';


});  // goog.scope
