'use strict';

goog.module('grrUi.semantic.semanticProtoDirective');
goog.module.declareLegacyNamespace();



/**
 * Returns value of a union type field in a union structure.
 *
 * @param {!Object} value Value to be converted to an array of items.
 * @param {!Object} descriptor Descriptor of the value.
 * @return {string} Union field value.
 * @throws {Error} when value and descriptor do not correspond to a union-type
 *     structure or when value of the union type field can't be determined
 *     (the latter shouldn't happen and means either a logic bug or a broken
 *     data structure).
 * @export
 */
exports.getUnionFieldValue = function(value, descriptor) {
  var unionFieldName = descriptor['union_field'];
  if (angular.isUndefined(unionFieldName)) {
    throw new Error('Not a union-type structure.');
  }

  if (angular.isDefined(value['value'][unionFieldName])) {
    return value['value'][unionFieldName]['value'].toLowerCase();
  } else {
    var fieldsLength = descriptor['fields'].length;
    for (var i = 0; i < fieldsLength; ++i) {
      var field = descriptor['fields'][i];
      if (field['name'] == unionFieldName) {
        return field['default']['value'].toLowerCase();
      }
    }
  }

  throw new Error('Can\'t determine value of the union field.');
};
var getUnionFieldValue = exports.getUnionFieldValue;


/**
 * Builds a list of items to display for union-type structures. These
 * structures have a field that determines which of its nested structures
 * should be used.
 *
 * @param {!Object} value Value to be converted to an array of items.
 * @param {!Object} descriptor Descriptor of the value to be converted to an
 *     array of items. Expected to have 'fields' attribute with list of fields
 *     descriptors.
 * @return {Array.<Object>} List of items to display. It will *always* have
 *     *only* union type field and a field that union type field value points
 *     to.
 * @export
 */
exports.buildUnionItems = function(value, descriptor) {
  var items = [];

  var unionFieldName = descriptor['union_field'];
  var unionFieldValue = getUnionFieldValue(value, descriptor);

  var fieldsLength = descriptor['fields'].length;
  for (var i = 0; i < fieldsLength; ++i) {
    var field = descriptor['fields'][i];
    var key = field['name'];
    if (key !== unionFieldName && key !== unionFieldValue) {
      continue;
    }
    var keyValue = value.value[key];
    if (angular.isUndefined(keyValue)) {
      keyValue = field['default'];
    }

    items.push({
      'value': keyValue,
      'key': field['friendly_name'] || field['name'],
      'desc': field['doc']
    });
  }

  return items;
};
var buildUnionItems = exports.buildUnionItems;


/**
 * Builds a list of items to display from a given non-union-type value. If value
 * has type descriptors, friendly names will be used as keys and
 * description will be filled in.
 *
 * @param {!Object} value Value to be converted to an array of items.
 * @param {!Object} descriptor Descriptor of the value to be converted to an
 *     array of items. Expected to have 'fields' attribute with list of fields
 *     descriptors.
 * @param {Object=} opt_visibleFields If provided, only shows fields with names
 *     from this list.
 * @param {Object=} opt_hiddenFields If provided, doesn't show fields with names
 *     from this list.
 * @return {Array.<Object>} List of items to display.
 * @export
 */
exports.buildNonUnionItems = function(
    value, descriptor, opt_visibleFields, opt_hiddenFields) {
  if (angular.isUndefined(descriptor['fields'])) {
    return [];
  }

  var items = [];

  var fieldsLength = descriptor['fields'].length;
  for (var i = 0; i < fieldsLength; ++i) {
    var field = descriptor['fields'][i];
    var key = field['name'];
    var keyValue = value.value[key];

    if (opt_visibleFields && opt_visibleFields.indexOf(key) == -1) {
      continue;
    }

    if (opt_hiddenFields && opt_hiddenFields.indexOf(key) != -1) {
      continue;
    }

    if (angular.isUndefined(keyValue)) {
      if (!opt_visibleFields) {
        continue;
      } else {
        keyValue = angular.copy(field['default']);
      }
    }
    items.push({
      'value': keyValue,
      'key': field['friendly_name'] || field['name'],
      'structKey': field['name'],
      'desc': field['doc'],
      'fieldDescriptor': field,
    });
  }

  return items;
};
var buildNonUnionItems = exports.buildNonUnionItems;


/**
 * Builds a list of items to display from the given value. If value
 * has type descriptors, friendly names will be used as keys and
 * description will be filled in.
 *
 * @param {!Object} value Value to be converted to an array of items.
 * @param {!Object} descriptor Descriptor of the value to be converted to an
 *     array of items. Expected to have 'fields' attribute with list of fields
 *     descriptors.
 * @param {Object=} opt_visibleFields If provided, only shows fields with names
 *     from this list.
 * @param {Object=} opt_hiddenFields If provided, doesn't show fields with names
 *     from this list.
 * @return {Array.<Object>} List of items to display.
 * @export
 */
exports.buildItems = function(
    value, descriptor, opt_visibleFields, opt_hiddenFields) {
  if (angular.isDefined(descriptor['union_field'])) {
    return buildUnionItems(value, descriptor);
  } else {
    return buildNonUnionItems(value,
                              descriptor,
                              opt_visibleFields,
                              opt_hiddenFields);
  }
};
var buildItems = exports.buildItems;

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

  /** @export {Array.<Object>} */
  this.items;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};


/**
 * Handles value changes.
 *
 * @param {Object} newValue
 * @param {Object} oldValue
 * @export
 */
SemanticProtoController.prototype.onValueChange = function(newValue, oldValue) {
  // newValue and oldValue are both undefined if the watcher is called to do
  // initialization before the value binding is actually set. In this case
  // we have to do nothing and wait until the watcher is called with a real
  // value.
  if (newValue === undefined && oldValue === undefined) {
    return;
  }

  if (angular.isObject(this.scope_['value'])) {
    var valueType = this.scope_['value']['type'];
    this.grrReflectionService_.getRDFValueDescriptor(valueType).then(
        function success(descriptor) {
          this.items = buildItems(this.scope_['value'],
                                  descriptor,
                                  this.scope_['visibleFields'],
                                  this.scope_['hiddenFields']);
        }.bind(this)); // TODO(user): Reflection failure scenario should be
                       // handled globally by reflection service.
  } else {
    this.items = [];
  }
};

/**
 * Directive that displays semantic proto fetched from the server.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.SemanticProtoDirective = function() {
  return {
    scope: {
      value: '=',
      visibleFields: '=',
      hiddenFields: '='
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
exports.SemanticProtoDirective.directive_name = 'grrSemanticProto';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.SemanticProtoDirective.semantic_type = 'RDFProtoStruct';
