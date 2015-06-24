'use strict';

goog.provide('grrUi.semantic.semanticProtoDirective.SemanticProtoDirective');

goog.scope(function() {



/**
 * Controller for SemanticProtoDirective.
 *
 * @param {!angular.Scope} $scope Directive's scope.
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @constructor
 * @ngInject
 */
var SemanticProtoController = function($scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

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
    var valueType = this.scope_.value['type'];
    this.grrReflectionService_.getRDFValueDescriptor(valueType).then(
        function success(descriptor) {
          this.items = this.buildItems(this.scope_.value, descriptor);
        }.bind(this)); // TODO(user): Reflection failure scenario should be
                       // handled globally by reflection service.
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
 * @param {!Object} descriptor Descriptor of the value to be converted to an
 *     array of items. Expected to have 'fields' attribute with list of fields
 *     descriptors.
 * @return {Array.<Object>} List of items to display.
 * @export
 * @suppress {missingProperties} as value can have arbitrary data.
 */
SemanticProtoController.prototype.buildItems = function(value, descriptor) {
  var items = [];

  var fieldsLength = descriptor.fields.length;
  for (var i = 0; i < fieldsLength; ++i) {
    var field = descriptor.fields[i];
    var key = field['name'];
    var keyValue = value.value[key];

    if (angular.isDefined(keyValue)) {
      items.push({
        'value': keyValue,
        'key': field['friendly_name'] || field['name'],
        'desc': field['doc']
      });
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

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.semanticProtoDirective.SemanticProtoDirective.semantic_type =
    'RDFProtoStruct';

});  // goog.scope
