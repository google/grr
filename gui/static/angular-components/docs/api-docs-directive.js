'use strict';

goog.provide('grrUi.docs.apiDocsDirective.ApiCallRendererDescriptor');
goog.provide('grrUi.docs.apiDocsDirective.ApiDocsController');
goog.provide('grrUi.docs.apiDocsDirective.ApiDocsDirective');
goog.provide('grrUi.docs.apiDocsDirective.ApiObjectRendererDescriptor');

goog.scope(function() {


/** @typedef {{
 *             route:string,
 *             methods:Array.<string>,
 *             doc:string,
 *             query_spec:Object.<string, Object>
 *           }}
 */
grrUi.docs.apiDocsDirective.ApiCallRendererDescriptor;


/** @typedef {{
 *             doc:string,
 *             query_spec:Object.<string, Object>
 *           }}
 */
grrUi.docs.apiDocsDirective.ApiObjectRendererDescriptor;



/**
 * Controller for ApiDocsDirective.
 *
 * @constructor
 * @param {angular.$http} $http The Angular http service.
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.docs.apiDocsDirective.ApiDocsController = function($http, grrApiService) {
  /** @private {angular.$http} */
  this.http_ = $http;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Array.<grrUi.docs.apiDocsDirective.ApiCallRendererDescriptor>} */
  this.apiCallRenderers;

  /** @export {Object.<string,
    *     grrUi.docs.apiDocsDirective.ApiObjectRendererDescriptor>}
    */
  this.apiObjectRenderers;

  /** @export {Object.<string, *>} */
  this.examplesByRenderer;

  this.grrApiService_.get('docs').then(this.onDocsFetched_.bind(this));
  this.http_.get('static/angular-components/docs/api-docs-examples.json').then(
      this.onExamplesFetched_.bind(this));
};

var ApiDocsController = grrUi.docs.apiDocsDirective.ApiDocsController;


/**
 * Handles response to the docs API request.
 *
 * @param {!Object} response
 * @private
 */
ApiDocsController.prototype.onDocsFetched_ = function(response) {
  this.apiCallRenderers = response.data['api_call_renderers'];
  this.apiObjectRenderers = response.data['api_object_renderers'];
};


/**
 * Handles response to the api-docs-examples.json request.
 *
 * @param {!Object} response
 * @private
 */
ApiDocsController.prototype.onExamplesFetched_ = function(response) {
  this.examplesByRenderer = response.data;
};



/**
 * Directive for displaying API documentation.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.docs.apiDocsDirective.ApiDocsDirective = function() {
  return {
    scope: {
    },
    restrict: 'E',
    templateUrl: 'static/angular-components/docs/api-docs.html',
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
grrUi.docs.apiDocsDirective.ApiDocsDirective.directive_name =
    'grrApiDocs';


});  // goog.scope
