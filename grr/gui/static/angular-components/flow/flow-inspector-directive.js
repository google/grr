'use strict';

goog.provide('grrUi.flow.flowInspectorDirective.FlowInspectorController');
goog.provide('grrUi.flow.flowInspectorDirective.FlowInspectorDirective');

goog.scope(function() {


/**
 * Controller for FlowInspectorDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.flow.flowInspectorDirective.FlowInspectorController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.activeTab = '';

  /** type {Object<string, boolean>} */
  this.tabsShown = {};

  this.scope_.$watch('activeTab', this.onDirectiveArgumentsChange_.bind(this));
  this.scope_.$watch('controller.activeTab', this.onTabChange_.bind(this));
};

var FlowInspectorController =
    grrUi.flow.flowInspectorDirective.FlowInspectorController;


/**
 * Handles changes to directive's arguments.'
 *
 * @param {string} newValue
 * @private
 */
FlowInspectorController.prototype.onDirectiveArgumentsChange_ = function(newValue) {
  if (angular.isString(newValue)) {
    this.activeTab = newValue;
  }
};

/**
 * Handles controller's activeTab attribute changes and propagates them to the
 * directive's scope.
 *
 * @param {string} newValue
 * @param {string} oldValue
 * @private
 */
FlowInspectorController.prototype.onTabChange_ = function(newValue, oldValue) {
  if (newValue !== oldValue) {
    this.scope_['activeTab'] = newValue;
  }
  this.tabsShown[newValue] = true;
};


/**
 * FlowInspectorDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.flow.flowInspectorDirective.FlowInspectorDirective = function() {
  return {
    scope: {
      flowId: '=',
      apiBasePath: '=',
      activeTab: '=?'
    },
    controller: FlowInspectorController,
    controllerAs: 'controller',
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flow-inspector.html'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.flowInspectorDirective.FlowInspectorDirective
    .directive_name = 'grrFlowInspector';



});  // goog.scope
