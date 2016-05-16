'use strict';

goog.provide('grrUi.core.splitterDirective.SplitterController');
goog.provide('grrUi.core.splitterDirective.SplitterDirective');
goog.provide('grrUi.core.splitterDirective.SplitterPaneDirective');

goog.scope(function() {



/**
 * Controller for SplitterDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!angular.$interval} $interval
 * @ngInject
 */
grrUi.core.splitterDirective.SplitterController = function(
    $scope, $element, $interval) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @type {string} */
  this.scope_.orientation;

  /** @export {!Array<angular.Scope>} */
  this.panes = [];
};


var SplitterController = grrUi.core.splitterDirective.SplitterController;


/**
 * Adds pane to the list of available panes.
 *
 * @param {!angular.Scope} pane
 * @export
 */
SplitterController.prototype.addPane = function(pane) {
  this.panes.push(pane);
};


/**
 * Links splitter to the DOM. This has to be called in the directive's link
 * function, as we're modifying directive's DOM.
 *
 */
/** @suppress {missingProperties} For jQuery.splitter(). */
SplitterController.prototype.link = function() {
  var closeableTo;
  if (angular.isDefined(this.scope_['closeableTo'])) {
    closeableTo = Number(this.scope_['closeableTo']);
  } else {
    closeableTo = 100;
  }

  var splitterOptions = {
    animSpeed: 50,
    closeableto: closeableTo,
    minAsize: this.scope_['minLeftPaneSize'] || 0,
    maxAsize: this.scope_['maxLeftPaneSize'] || 3000
  };

  if (this.scope_.orientation === 'horizontal') {
    splitterOptions['splitHorizontal'] = true;
  } else if (this.scope_.orientation === 'vertical') {
    splitterOptions['splitVertical'] = true;
  } else {
    throw Error('Orientation can be either "vertical" or "horizontal".');
  }

  splitterOptions['A'] = $(this.panes[0].elem);
  splitterOptions['B'] = $(this.panes[1].elem);

  // Wait until DOM updates so that splitter is applied to a div that
  // has a meaningful width and height. Give up after 5 attempts.
  var count = 0;
  var stop;
  var registerSplitter = function() {
    if ($(this.element_).width() > 0 &&
        $(this.element_).height() > 0 ||
        count > 5) {
      $(this.element_).children('div.splitter').splitter(splitterOptions);
      this.interval_.cancel(stop);
    } else {
      count += 1;
    }
  }.bind(this);
  stop = this.interval_(registerSplitter, 100);
  registerSplitter();

  this.element_.on('$destroy', function() {
    this.interval_.cancel(stop);
  }.bind(this));
};



/**
 * Displays the splitter with 2 panes defined via grr-splitter-pane directives.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.splitterDirective.SplitterDirective = function() {
  return {
    scope: {
      orientation: '@',
      closeableTo: '@',
      minLeftPaneSize: '@',
      maxLeftPaneSize: '@'
    },
    restrict: 'EA',
    transclude: true,
    template: '<div class="splitter fill-parent no-margins" ' +
        'ng-transclude></div>',
    controller: SplitterController,
    controllerAs: 'controller',
    link: function(scope, element, attrs) {
      scope.controller.link();
    }
  };
};


/**
 * Name of the directive as registered in Angular.
 *
 * @const
 * @export
 */
grrUi.core.splitterDirective.SplitterDirective.directive_name =
    'grrSplitter';



/**
 * Registers splitter pane in the splitter.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.splitterDirective.SplitterPaneDirective = function() {
  return {
    scope: {},
    restrict: 'EA',
    require: '^grrSplitter',
    transclude: true,
    template: '<div class="fill-parent no-margins" ng-transclude></div>',
    link: function(scope, element, attrs, grrSplitterCtrl) {
      scope.elem = element;
      grrSplitterCtrl.addPane(scope);
    }
  };
};


/**
 * Name of the directive as registered in Angular.
 *
 * @const
 * @export
 */
grrUi.core.splitterDirective.SplitterPaneDirective.directive_name =
    'grrSplitterPane';

});  // goog.scope
