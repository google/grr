goog.module('grrUi.core.splitterDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for SplitterDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!angular.$interval} $interval
 * @ngInject
 */
const SplitterController = function(
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
  // Find how many panes do not have a size set and calculate default
  // size for them by dividing available size by their count.
  let sizeLeft = 100;
  let sizeLeftCount = 0;
  this.panes.forEach((pane) => {
    if (pane['size']) {
      sizeLeft -= parseInt(pane['size'], 10);
    } else {
      ++sizeLeftCount;
    }
  });
  const defaultSize = sizeLeft / sizeLeftCount;

  const splitterOptions = {
    gutterSize: 4,
    sizes: this.panes.map(pane => parseInt(pane['size'] || defaultSize, 10))
  };

  // grr-splitter assumes that 'orientation' means orientation of the splitter's
  // gutter bar. I.e. 2 panes with one on top of another mean a 'horizontal'
  // splitter (in a sense of a 'horizontal line'). Split.js, on the other hand,
  // has a notion of 'direction' which corresponds to panes direction.
  if (this.scope_['orientation'] == 'horizontal') {
    splitterOptions['direction'] = 'vertical';
  } else if (this.scope_['orientation'] === 'vertical') {
    splitterOptions['direction'] = 'horizontal';
  } else {
    throw Error('Orientation can be either "vertical" or "horizontal".');
  }

  const elems = this.panes.map(pane => pane['elem']);

  // Wait until DOM updates so that splitter is applied to a div that
  // has a meaningful width and height. Give up after 5 attempts.
  var count = 0;
  var stop;
  var registerSplitter = function() {
    if ($(this.element_).width() > 0 &&
        $(this.element_).height() > 0 ||
        count > 5) {
      Split(elems, splitterOptions);
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
 * @return {!angular.Directive}
 * @ngInject
 * @export
 */
exports.SplitterDirective = function() {
  return {
    scope: {
      orientation: '@',
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
exports.SplitterDirective.directive_name = 'grrSplitter';



/**
 * Registers splitter pane in the splitter.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.SplitterPaneDirective = function() {
  return {
    scope: {
      size: '@' // Size is expressed in percents (for example: 25, 75, etc).
    },
    restrict: 'EA',
    require: '^grrSplitter',
    transclude: true,
    template: '<div class="fill-parent no-margins" ng-transclude></div>',
    link: function(scope, element, attrs, grrSplitterCtrl) {
      scope['elem'] = element[0];
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
exports.SplitterPaneDirective.directive_name = 'grrSplitterPane';
