'use strict';

goog.module('grrUi.docs.apiDocsDirective');
goog.module.declareLegacyNamespace();

const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');


/**
 * Controller for ApiDocsDirective.
 *
 * @constructor
 * @param {!angular.jQuery} $element
 * @param {angular.$http} $http The Angular http service.
 * @param {!ApiService} grrApiService
 * @ngInject
 */
const ApiDocsController = function($element, $http,
                                                         grrApiService) {
  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {angular.$http} */
  this.http_ = $http;

  /** @private {!ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {!Object<string, Array<Object>>} */
  this.apiMethodsByCategory;

  /** @export {Object<string, *>} */
  this.examplesByMethod;

  /** @export {Array<string>} */
  this.categories;

  /** @export {string} */
  this.visibleCategory;

  this.grrApiService_.get('reflection/api-methods').then(
      this.onApiMethodsListFetched_.bind(this));
  this.http_.get('/static/angular-components/docs/api-docs-examples.json').then(
      this.onExamplesFetched_.bind(this));
};


/**
 * Handles response to the docs API request.
 *
 * @param {!Object} response
 * @private
 */
ApiDocsController.prototype.onApiMethodsListFetched_ = function(response) {
  var categoriesDict = {};
  var items = stripTypeInfo(response['data']['items']);
  angular.forEach(/** @type {Array<Object>} */ (items), function(descriptor) {
    var category = descriptor['category'];
    if (!category) {
      category = 'Other';
    }

    if (categoriesDict[category] === undefined) {
      categoriesDict[category] = [];
    }
    categoriesDict[category].push(descriptor);
  }.bind(this));

  angular.forEach(categoriesDict, function(descriptors) {
    descriptors.sort(function(a, b) {
      var astr = a['name'] + '_' + a['http_route'];
      var bstr = b['name'] + '_' + b['http_route'];
      if (astr > bstr) {
        return 1;
      } else if (astr < bstr) {
        return -1;
      } else {
        return 0;
      }
    });
  }.bind(this));
  this.apiMethodsByCategory = categoriesDict;
  this.categories = Object.keys(categoriesDict).sort();
  this.visibleCategory = this.categories[0];
};


/**
 * Handles response to the api-docs-examples.json request.
 *
 * @param {!Object} response
 * @private
 */
ApiDocsController.prototype.onExamplesFetched_ = function(response) {
  this.examplesByMethod = {};
  angular.forEach(response.data, function(handlerExamples) {
    angular.forEach(handlerExamples, function(example) {
      var apiMethod = example['api_method'];
      if (!this.examplesByMethod[apiMethod]) {
        this.examplesByMethod[apiMethod] = [];
      }
      this.examplesByMethod[apiMethod].push(example);
    }.bind(this));
  }.bind(this));
};


/**
 * Handles clicks on category links.
 *
 * @param {string} category Category name.
 * @export
 */
ApiDocsController.prototype.onCategoryLinkClick = function(category) {
  var index = this.categories.indexOf(category);
  var headingElement = $('#docs-category-' + index.toString());

  /**
   * We have to find a scrollable container that actually has the scrollbars.
   * This container may be anywhere up in the ancestors hierarchy.
   * Scrollable container has to satisfy 2 conditions:
   * 1) It should either be already scrolled (scrollTop() > 0) or it's
   *    scrollable height should be more than its physical height.
   * 2) scrollTop() values should change when scrollTop(offset) is called.
   *    Changing scrollTop() value means that container has actually
   *    scrolled.
   */
  var scrollableContainer = headingElement.parent();
  while (scrollableContainer.length != 0) {
    if (scrollableContainer.scrollTop() > 0 ||
        Math.abs(scrollableContainer[0].clientHeight -
        scrollableContainer[0].scrollHeight) > 1) {

      var offset = headingElement.offset()['top'] -
          scrollableContainer.offset()['top'] +
          scrollableContainer.scrollTop();
      var prevOffset = scrollableContainer.scrollTop();
      scrollableContainer.scrollTop(/** @type {number} */ (offset));

      /**
       * This approach is a bit hacky, but seems to work. Container is truly
       * scrollable if it's scrollTop() value changes after scrollTop(offset)
       * was called. Therefore we stop searching for scrollable parent
       * if this condition is satisfied.
       *
       * One exception to the approach above is when container is already
       * scrolled to the right place. Then we also consider the container
       * to be the scrollable container we were searching for and break.
       * Probability of having 2 containers scrolled to exactly the same
       * point is low, so even though this algorithm is not strictly
       * deterministic, it's fine for the needs of the docs page.
       */
      if (scrollableContainer.scrollTop() != prevOffset ||
          Math.abs(prevOffset - offset) <= 1) {
        break;
      }
    }
    scrollableContainer = scrollableContainer.parent();
  }
};



/**
 * Directive for displaying API documentation.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ApiDocsDirective = function() {
  return {
    scope: {
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/docs/api-docs.html',
    controller: ApiDocsController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ApiDocsDirective.directive_name = 'grrApiDocs';
