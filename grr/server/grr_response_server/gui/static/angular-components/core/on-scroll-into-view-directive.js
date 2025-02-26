goog.module('grrUi.core.onScrollIntoViewDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for OnScrollIntoViewDirective.
 * @unrestricted
 */
const OnScrollIntoViewController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.jQuery} $element
   * @param {!angular.Attributes} $attrs
   * @param {!angular.$interval} $interval
   * @param {!angular.$window} $window
   * @ngInject
   */
  constructor($scope, $element, $attrs, $interval, $window) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.Attributes} */
    this.attrs_ = $attrs;

    /** @private {!angular.jQuery} */
    this.element_ = $element;

    /** @private {!angular.$window} */
    this.window_ = $window;

    /** @type {boolean} */
    this.currentlyVisible = false;

    const stop = $interval(this.onInterval.bind(this), 100);
    $scope.$on('$destroy', function() {
      $interval.cancel(stop);
    });
  }

  /**
   * Handles $interval events. Evaluates grr-on-scroll-into-view attribute
   * if element became visible.
   */
  onInterval() {
    const elemOffset = $(this.element_).offset();
    const elemWidth = $(this.element_).width();
    const elemHeight = $(this.element_).height();

    let elem = document.elementFromPoint(
        elemOffset.left - $(this.window_).scrollLeft() + 1,
        elemOffset.top - $(this.window_).scrollTop() + 1);
    let isVisible = (elem == $(this.element_)[0]);

    if (!isVisible) {
      elem = document.elementFromPoint(
          elemOffset.left + elemWidth - $(this.window_).scrollLeft() - 1,
          elemOffset.top + elemHeight - $(this.window_).scrollTop() - 1);
      isVisible = (elem == $(this.element_)[0]);
    }

    if (!isVisible) {
      elem = document.elementFromPoint(
          elemOffset.left + elemWidth / 2 - $(this.window_).scrollLeft(),
          elemOffset.top + elemHeight / 2 - $(this.window_).scrollTop());
      isVisible = (elem == $(this.element_)[0]);
    }

    if (this.currentlyVisible != isVisible) {
      this.currentlyVisible = isVisible;
      if (isVisible) {
        this.scope_.$eval(this.attrs_['grrOnScrollIntoView']);
      }
    }
  }
};



/**
 * Directive that triggers custom user action when element scrolls into view.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.OnScrollIntoViewDirective = function() {
  return {restrict: 'A', controller: OnScrollIntoViewController};
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.OnScrollIntoViewDirective.directive_name = 'grrOnScrollIntoView';
