'use strict';

goog.provide('grrUi.semantic.semanticVersionedProtoDirective.SemanticVersionedProtoController');
goog.provide('grrUi.semantic.semanticVersionedProtoDirective.SemanticVersionedProtoDirective');
goog.require('grrUi.semantic.semanticProtoDirective.buildItems');

goog.scope(function() {


/**
 * Controller for SemanticVersionedProtoDirective.
 *
 * @param {!angular.Scope} $scope Directive's scope.
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @constructor
 * @ngInject
 */
var SemanticVersionedProtoController = function($scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @export {Array<Object>} */
  this.items = [];

  this.scope_.$watch('::value', this.onValueChange_.bind(this));
};


/**
 * Annotates items with properties necessary to show them in the template.
 *
 * @param {Array<Object>} items Items built by grr-semantic-proto's buildItems.
 * @param {!Object<string, Object>} descriptors Dictionary with descriptors for
 *     all the types used by the items.
 * @return {Array<Object>} Processed items.
 *
 * @private
 */
SemanticVersionedProtoController.prototype.processItems_ = function(
    items, descriptors) {

  angular.forEach(items, function(item) {
    var itemType = item['fieldDescriptor']['type'];
    item['recursiveItem'] = (
        this.scope_['historyDepth'] > 1 &&
            descriptors[itemType]['kind'] === 'struct' &&
            !item['fieldDescriptor']['repeated'] &&
            !item['fieldDescriptor']['dynamic']);

    if (!this.scope_['historyPath']) {
      item['historyPath'] = item['structKey'];
    } else {
      item['historyPath'] = this.scope_['historyPath'] +
          '.' + item['structKey'];
    }
  }.bind(this));

  return items;
};


/**
 * Handles value changes.
 *
 * @private
 */
SemanticVersionedProtoController.prototype.onValueChange_ = function() {
  if (angular.isObject(this.scope_['value'])) {
    var valueType = this.scope_['value']['type'];
    this.grrReflectionService_.getRDFValueDescriptor(valueType, true).then(
        function success(descriptors) {
          var items = grrUi.semantic.semanticProtoDirective.buildItems(
              this.scope_['value'],
              descriptors[valueType]);
          this.items = this.processItems_(items, descriptors);
        }.bind(this)); // TODO(user): Reflection failure scenario should be
                       // handled globally by reflection service.
  } else {
    this.items = [];
  }
};


/**
 * Directive that displays semantic proto fetched from the server.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.semantic.semanticVersionedProtoDirective.SemanticVersionedProtoDirective = function() {
  return {
    scope: {
      value: '=',
      onFieldClick: '&',
      historyDepth: '=',
      historyPath: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/semantic-versioned-proto.html',
    controller: SemanticVersionedProtoController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.semanticVersionedProtoDirective.SemanticVersionedProtoDirective.directive_name =
    'grrSemanticVersionedProto';

});  // goog.scope
