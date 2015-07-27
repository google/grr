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
 * @param {!angular.JQLite} $element
 * @ngInject
 */
grrUi.core.splitterDirective.SplitterController = function(
    $scope, $element) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.orientation;

  /** @private {!angular.JQLite} */
  this.element_ = $element;

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
    closeableto: closeableTo
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

  // TODO(user): check if this is really needed.
  if (this.scope_.orientation === 'horizontal') {
    var height = $(this.element_).height();
    splitterOptions['A'].height(height / 2);
    splitterOptions['B'].height(height / 2);
  }

  $(this.element_).children('div.splitter').splitter(splitterOptions);

  // TODO(user): check if this call is really needed.
  $(this.element_).children('div.splitter').resize();
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
      closeableTo: '@'
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
