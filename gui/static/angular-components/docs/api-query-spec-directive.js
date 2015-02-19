'use strict';

goog.provide('grrUi.docs.apiQuerySpecDirective.ApiQuerySpecController');
goog.provide('grrUi.docs.apiQuerySpecDirective.ApiQuerySpecDirective');

goog.provide('grrUi.docs.apiQuerySpecDirective.QueryParamSpec');

goog.scope(function() {


/** @typedef {{
 *             type:string,
 *             required:boolean,
 *             doc:string,
 *             default:*
 *           }}
 */
grrUi.docs.apiQuerySpecDirective.QueryParamSpec;



/**
 * Controller for ApiQuerySpecDirective..
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.docs.apiQuerySpecDirective.ApiQuerySpecController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @export {grrUi.docs.apiQuerySpecDirective.QueryParamSpec} */
  this.value;

  this.scope_.$watch('value', this.onValueChange.bind(this));
};

var ApiQuerySpecController =
    grrUi.docs.apiQuerySpecDirective.ApiQuerySpecController;


/**
 * Handles value attribute changes.
 *
 * @param {grrUi.docs.apiQuerySpecDirective.QueryParamSpec} newValue New
 *     query spec value.
 * @export
 */
ApiQuerySpecController.prototype.onValueChange = function(newValue) {
  this.value = newValue;
};



/**
 * Directive for displaying API query specificiation.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.docs.apiQuerySpecDirective.ApiQuerySpecDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: 'static/angular-components/docs/api-query-spec.html',
    controller: ApiQuerySpecController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.docs.apiQuerySpecDirective.ApiQuerySpecDirective.directive_name =
    'grrApiQuerySpec';


});  // goog.scope
