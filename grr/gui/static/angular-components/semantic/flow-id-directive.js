'use strict';

goog.module('grrUi.semantic.flowIdDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for FlowIdDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
const FlowIdController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.clientId;
};


/**
 * Directive that displays ApiFlowId values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @export
 */
exports.FlowIdDirective = function() {
  return {
    scope: {
      value: '='
    },
    require: '?^grrClientContext',
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/flow-id.html',
    controller: FlowIdController,
    controllerAs: 'controller',
    link: function(scope, element, attrs, grrClientContextCtrl) {
      if (grrClientContextCtrl) {
        scope['controller'].clientId = grrClientContextCtrl.clientId;
      }
    }
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.FlowIdDirective.directive_name = 'grrFlowId';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.FlowIdDirective.semantic_type = 'ApiFlowId';
