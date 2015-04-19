'use strict';

goog.provide('grrUi.semantic.semanticProtoDirective.SemanticProtoDirective');

goog.require('grrUi.semantic.SemanticDirectivesRegistry');

goog.scope(function() {



/**
 * Controller for SemanticProtoDirective.
 *
 * @param {!angular.Scope} $scope Directive's scope.
 * @constructor
 * @ngInject
 */
var SemanticProtoController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Object} */
  this.scope_.value;

  /** @export {Array.<Object>} */
  this.items = [];

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};


/**
 * Handles value changes.
 *
 * @export
 */
SemanticProtoController.prototype.onValueChange = function() {
  if (angular.isObject(this.scope_.value)) {
    this.items = this.buildItems(this.scope_.value);
  } else {
    this.items = [];
  }
};


/**
 * Builds a list of items to display from the given value. If value
 * has type descriptors, friendly names will be used as keys and
 * description will be filled in.
 *
 * @param {!Object} value Value to be converted to an array of items.
 * @return {Array.<Object>} List of items to display.
 * @export
 * @suppress {missingProperties} as value can have arbitrary data.
 */
SemanticProtoController.prototype.buildItems = function(value) {
  var items = [];

  var fieldsOrderLength = value.fields_order.length;
  for (var i = 0; i < fieldsOrderLength; ++i) {
    var key = value.fields_order[i];
    var keyValue = value.value[key];

    if (value.metadata !== undefined &&
        value.metadata[key] !== undefined) {
      items.push({
        'value': keyValue,
        'key': value.metadata[key].friendly_name,
        'desc': value.metadata[key].description
      });
    } else {
      items.push({'value': keyValue, 'key': key});
    }
  }

  return items;
};



/**
 * Directive that displays semantic proto fetched from the server.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.semanticProtoDirective.SemanticProtoDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/semantic-proto.html',
    controller: SemanticProtoController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.semanticProtoDirective.SemanticProtoDirective.directive_name =
    'grrSemanticProto';

grrUi.semantic.SemanticDirectivesRegistry.registerDirective(
    'RDFProtoStruct',
    grrUi.semantic.semanticProtoDirective.SemanticProtoDirective);


});  // goog.scope
