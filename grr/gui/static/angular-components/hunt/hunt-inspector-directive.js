'use strict';

goog.provide('grrUi.hunt.huntInspectorDirective');
goog.provide('grrUi.hunt.huntInspectorDirective.HuntInspectorDirective');
goog.provide('grrUi.hunt.huntInspectorDirective.huntInspectorController');

goog.scope(function() {


/**
 * Controller for HuntInspectorDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.hunt.huntInspectorDirective.huntInspectorController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.shownHuntUrn;

  /** @type {string} */
  this.activeTab = '';

  /** type {Object<string, boolean>} */
  this.tabsShown = {};

  this.scope_.$watchGroup(['huntUrn', 'activeTab'], this.onDirectiveArgumentsChange_.bind(this));
  this.scope_.$watch('controller.activeTab', this.onTabChange_.bind(this));
};

var HuntInspectorController =
    grrUi.hunt.huntInspectorDirective.huntInspectorController;


/**
 * Handles huntUrn and activeTab scope attribute changes.
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
    this.shownHuntUrn = this.scope_['huntUrn'];
  }.bind(this));
};

/**
 * Handles huntUrn scope attribute changes.
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
grrUi.hunt.huntInspectorDirective.HuntInspectorDirective = function() {
  return {
    scope: {
      huntUrn: '=',
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
grrUi.hunt.huntInspectorDirective.HuntInspectorDirective.directive_name =
    'grrHuntInspector';

});  // goog.scope
