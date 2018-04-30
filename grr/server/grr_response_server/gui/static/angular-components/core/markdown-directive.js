'use strict';

goog.module('grrUi.core.markdownDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for MarkdownDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!angular.$window} $window
 * @constructor
 * @ngInject
 */
const MarkdownController = function($scope, $element, $window) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!angular.$window} */
  this.window_ = $window;

  this.scope_.$watch('source', this.onSourceChange_.bind(this));
};


/**
 * Handles changes in 'source' binding.
 *
 * @param {string} newValue
 * @private
 */
MarkdownController.prototype.onSourceChange_ = function(newValue) {
  this.element_.html('');

  if (angular.isDefined(newValue)) {
    // marked() is part of the "marked" library.
    this.element_.html(marked(newValue));
  }
};


/**
 * Directive that displays rendered markdown text.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.MarkdownDirective = function() {
  return {
    scope: {
      source: '='
    },
    restrict: 'E',
    controller: MarkdownController
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.MarkdownDirective.directive_name = 'grrMarkdown';
