'use strict';

goog.provide('grrUi.client.clientUsernamesDirective.ClientUsernamesController');
goog.provide('grrUi.client.clientUsernamesDirective.ClientUsernamesDirective');


goog.scope(function() {


/**
 * Controller for ClientUsernamesDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
grrUi.client.clientUsernamesDirective.ClientUsernamesController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {Array<?>} */
  this.scope_.usernames;

  this.scope_.$watch('::value', this.onValueChange_.bind(this));
};

var ClientUsernamesController =
    grrUi.client.clientUsernamesDirective.ClientUsernamesController;


/**
 * Handles changes of scope.value attribute.
 * @private.
 *
 */
ClientUsernamesController.prototype.onValueChange_ = function() {
  if (angular.isDefined(this.scope_.value)) {
    var users = this.scope_.value.value.split(' ');
    var array = [];
    angular.forEach(users, function(value) {
      array.push({'type': 'RDFString', 'value': value});
    });
    this.scope_.usernames = array;
  }
};

/**
 * Directive that displays usernames for a given client.
 * It separates a string of usernames on a client by the space character into a
 * list of objects, and delegates rendering of it to grr-semantic-value.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.client.clientUsernamesDirective.ClientUsernamesDirective = function() {
  return {
    scope: {value: '='},
    restrict: 'E', template: '<grr-semantic-value value="::usernames" />',
    controller: ClientUsernamesController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 */
grrUi.client.clientUsernamesDirective.ClientUsernamesDirective.directive_name =
    'grrClientUsernames';
});  // goog.scope
