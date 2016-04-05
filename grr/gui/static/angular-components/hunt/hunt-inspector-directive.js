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
  this.scope_.huntUrn;

  this.shownHuntUrn = undefined;

  this.scope_.$watch('huntUrn', this.onHuntUrnChange.bind(this));
};

var HuntInspectorController =
    grrUi.hunt.huntInspectorDirective.huntInspectorController;


/**
 * Handles huntUrn scope attribute changes.
 */
HuntInspectorController.prototype.onHuntUrnChange = function() {
  // Doing this asynchronously so that ng-if clause in the template gets
  // triggered. This ensures that new hunt information gets properly
  // rerendered.
  this.scope_.$evalAsync(function() {
    this.shownHuntUrn = this.scope_.huntUrn;
  }.bind(this));
};


/**
 * HuntInspectorDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.hunt.huntInspectorDirective.HuntInspectorDirective = function() {
  return {
    scope: {
      huntUrn: '='
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
