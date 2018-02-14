'use strict';

goog.module('grrUi.hunt.huntInspectorDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for HuntInspectorDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const HuntInspectorController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.shownHuntId;

  /** @type {string} */
  this.activeTab = '';

  /** type {Object<string, boolean>} */
  this.tabsShown = {};

  this.scope_.$watchGroup(['huntId', 'activeTab'], this.onDirectiveArgumentsChange_.bind(this));
  this.scope_.$watch('controller.activeTab', this.onTabChange_.bind(this));
};



/**
 * Handles huntId and activeTab scope attribute changes.
 *
 * @private
 */
HuntInspectorController.prototype.onDirectiveArgumentsChange_ = function() {
  if (angular.isString(this.scope_['activeTab'])) {
    this.activeTab = this.scope_['activeTab'];
  }

  // Doing this asynchronously so that ng-if clause in the template gets
  // triggered. This ensures that new hunt information gets properly
  // rerendered.
  this.scope_.$evalAsync(function() {
    this.shownHuntId = this.scope_['huntId'];
  }.bind(this));
};

/**
 * Handles huntId scope attribute changes.
 *
 * @param {string} newValue
 * @param {string} oldValue
 * @private
 */
HuntInspectorController.prototype.onTabChange_ = function(newValue, oldValue) {
  if (newValue !== oldValue) {
    this.scope_['activeTab'] = newValue;
  }
  this.tabsShown[newValue] = true;
};


/**
 * HuntInspectorDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
exports.HuntInspectorDirective = function() {
  return {
    scope: {
      huntId: '=',
      activeTab: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-inspector.html',
    controller: HuntInspectorController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.HuntInspectorDirective.directive_name = 'grrHuntInspector';
