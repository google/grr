goog.module('grrUi.client.clientUsernamesDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ClientUsernamesDirective.
 * @unrestricted
 */
const ClientUsernamesController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {Array<?>} */
    this.scope_.usernames;

    this.scope_.$watch('::value', this.onValueChange_.bind(this));
  }

  /**
   * Handles changes of scope.value attribute.
   * @private.
   *
   */
  onValueChange_() {
    if (angular.isDefined(this.scope_.value)) {
      const users = this.scope_.value.value.split(' ');
      const array = [];
      angular.forEach(users, function(value) {
        array.push({'type': 'RDFString', 'value': value});
      });
      this.scope_.usernames = array;
    }
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
exports.ClientUsernamesDirective = function() {
  return {
    scope: {value: '='},
    restrict: 'E',
    template: '<grr-semantic-value value="::usernames"></grr-semantic-value>',
    controller: ClientUsernamesController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 */
exports.ClientUsernamesDirective.directive_name = 'grrClientUsernames';
