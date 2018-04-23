'use strict';

goog.module('grrUi.semantic.semanticVersionedProtoDirective');
goog.module.declareLegacyNamespace();

const {buildNonUnionItems} = goog.require('grrUi.semantic.semanticProtoDirective');



/**
 * Controller for SemanticVersionedProtoDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope Directive's scope.
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
var SemanticVersionedProtoController = function($scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @export {Array<Object>} */
  this.items;

  this.scope_.$watch('::value', this.onValueChange_.bind(this));
};


/**
 * Annotates items with properties necessary to show them in the template.
 *
 * @param {Array<Object>} items Items built by grr-semantic-proto's
 *     buildNonUnionItems.
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
 * @param {Object} newValue
 * @param {Object} oldValue
 * @private
 */
SemanticVersionedProtoController.prototype.onValueChange_ = function(
    newValue, oldValue) {
  // newValue and oldValue are both undefined if the watcher is called to do
  // initialization before the value binding is actually set. In this case
  // we have to do nothing and wait until the watcher is called with a real
  // value.
  if (newValue === undefined && oldValue === undefined) {
    return;
  }

  if (angular.isObject(this.scope_['value'])) {
    var valueType = this.scope_['value']['type'];
    this.grrReflectionService_.getRDFValueDescriptor(valueType, true)
        .then(function success(descriptors) {
          var items =
              buildNonUnionItems(this.scope_['value'], descriptors[valueType]);
          this.items = this.processItems_(items, descriptors);
        }.bind(this));  // TODO(user): Reflection failure scenario should be
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
exports.SemanticVersionedProtoDirective = function() {
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
exports.SemanticVersionedProtoDirective.directive_name =
    'grrSemanticVersionedProto';
