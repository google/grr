'use strict';

goog.provide('grrUi.semantic.jsonDirective.JsonController');
goog.provide('grrUi.semantic.jsonDirective.JsonDirective');

goog.scope(function() {


/**
 * Controller for JsonDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$window} $window
 * @constructor
 * @ngInject
 */
grrUi.semantic.jsonDirective.JsonController = function(
    $scope, $window) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$window} */
  this.window_ = $window;

  /** @type {string} */
  this.prettyJson;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};

var JsonController =
    grrUi.semantic.jsonDirective.JsonController;


/**
 * Handles changes of scope.value attribute.
 *
 * @param {number} newValue Timestamp value in microseconds.
 * @suppress {missingProperties} as value can be anything.
 */
JsonController.prototype.onValueChange = function(newValue) {
  var jsonStr = newValue.value;
  if (angular.isString(jsonStr)) {
    try {
      var parsedJson = JSON.parse(jsonStr);
      this.prettyJson = JSON.stringify(parsedJson, null, 2);
    } catch (err) {
      this.prettyJson = 'jsonerror(' + err.message + '):' + jsonStr;
    }
  } else {
    this.prettyJson = '';
  }
};



/**
 * Directive that displays Json values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.jsonDirective.JsonDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/json.html',
    controller: JsonController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.jsonDirective.JsonDirective.directive_name =
    'grrJson';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.jsonDirective.JsonDirective.semantic_type =
    'ZippedJSONBytes';


});  // goog.scope
