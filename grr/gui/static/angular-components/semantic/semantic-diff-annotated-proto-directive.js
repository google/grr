'use strict';

goog.module('grrUi.semantic.semanticDiffAnnotatedProtoDirective');
goog.module.declareLegacyNamespace();

const {buildItems} = goog.require('grrUi.semantic.semanticProtoDirective');



/**
 * Controller for SemanticDiffAnnotatedProtoDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope Directive's scope.
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
var SemanticDiffAnnotatedProtoController = function(
    $scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {Array<Object>} */
  this.items;

  this.scope_.$watch('::value', this.onValueChange_.bind(this));
};


/**
 * Handles value changes.
 *
 * @param {Object} newValue
 * @param {Object} oldValue
 * @private
 */
SemanticDiffAnnotatedProtoController.prototype.onValueChange_ = function(
    newValue, oldValue) {
  // newValue and oldValue are both undefined if the watcher is called to do
  // initialization before the value binding is actually set. In this case
  // we have to do nothing and wait until the watcher is called with a real
  // value.
  if (newValue === undefined && oldValue === undefined) {
    return;
  }

  if (angular.isObject(this.scope_['value'])) {
    this.grrReflectionService_.getRDFValueDescriptor(
        this.scope_['value']['type']).then(
            // TODO(user): Reflection failure scenario should be
            // handled globally by reflection service.
            function success(descriptor) {
              this.items = buildItems(this.scope_['value'],
                                      descriptor,
                                      this.scope_['visibleFields'],
                                      this.scope_['hiddenFields']);

              // It's easier and more efficient to check for array-like
              // values here and set 'isList' attribute than to do it
              // in the directive template.
              angular.forEach(this.items, function(item) {
                item['isList'] = angular.isArray(item['value']);
              }.bind(this));
            }.bind(this));
  } else {
    this.items = [];
  }
};


/**
 * Directive that displays semantic proto with diff annotations. These
 * annotations are expected to be added by
 * grrUi.semantic.semanticProtosDiffDirective.diffAnnotate function (see
 * its documentation for details).
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.SemanticDiffAnnotatedProtoDirective = function() {
  return {
    scope: {
      value: '=',
      visibleFields: '=',
      hiddenFields: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/' +
        'semantic-diff-annotated-proto.html',
    controller: SemanticDiffAnnotatedProtoController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.SemanticDiffAnnotatedProtoDirective.directive_name =
    'grrSemanticDiffAnnotatedProto';
