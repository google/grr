
'use strict';

goog.provide('grrUi.core.bindKeyDirective.BindKeyController');
goog.provide('grrUi.core.bindKeyDirective.BindKeyDirective');

goog.scope(function() {

/**
 * Controller for BindKeyDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!angular.Attributes} $attrs
 * @constructor
 * @ngInject
 */
grrUi.core.bindKeyDirective.BindKeyController =
    function($scope, $element, $attrs) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {number} */
  this.key_ = 13; // Set to ENTER by default.

  /** @private {string} */
  this.callbackExpr_;

  if ($attrs['key']) {
    this.key_ = parseInt($attrs['key'], 10);
  }

  if ($attrs['grrBindKey']) {
    this.callbackExpr_ = /** @type {string} */ (
        $attrs['grrBindKey']);
  }

  $element.bind("keydown, keypress", this.onKeyDown_.bind(this));
};

var BindKeyController =
    grrUi.core.bindKeyDirective.BindKeyController;

/**
 * Updates the bindKey based on the current time.
 *
 * @param {Object} event
 * @private
 */
BindKeyController.prototype.onKeyDown_ = function(event) {
  if (event['which'] === this.key_) {
    this.scope_.$apply(function(){
      this.scope_.$eval(this.callbackExpr_);
    }.bind(this));

    event.preventDefault();
  }
};

/**
 * Directive that displays RDFDatetime values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.bindKeyDirective.BindKeyDirective = function() {
  return {
    restrict: 'A',
    controller: BindKeyController
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.core.bindKeyDirective.BindKeyDirective.directive_name =
    'grrBindKey';

});  // goog.scope
