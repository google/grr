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
 * @export
 * @suppress {missingProperties} as value can have arbitrary data.
 */
SemanticProtoController.prototype.buildItems = function(value) {
  var items = [];

  angular.forEach(value.fields_order, function(key) {
    if (value.descriptors !== undefined &&
        value.descriptors[key] !== undefined) {
      items.push({
        'value': value.value[key],
        'key': value.descriptors[key].friendly_name,
        'desc': value.descriptors[key].description
      });
    } else {
      items.push({'value': value.value[key], 'key': key});
    }

    if (angular.isDefined(value.value[key + '_fetch_more_url'])) {
      items.push({
        'key': '',
        'fetch_more_url': true,
        'value': value[key + 'fetch_more_url']
      });
    }
  });

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
