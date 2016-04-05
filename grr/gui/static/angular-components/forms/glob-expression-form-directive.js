'use strict';

goog.provide('grrUi.forms.globExpressionFormDirective.GlobExpressionFormController');
goog.provide('grrUi.forms.globExpressionFormDirective.GlobExpressionFormDirective');


goog.scope(function() {

/**
 * Controller for GlobExpressionFormDirective.
 *
 * @constructor
 * @param {!angular.jQuery} $element
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.forms.globExpressionFormDirective.GlobExpressionFormController = function(
    $element, $interval, grrApiService) {

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  this.grrApiService_.get('/clients/kb-fields').then(
      this.onGetFields_.bind(this));
};
var GlobExpressionFormController =
    grrUi.forms.globExpressionFormDirective.GlobExpressionFormController;


/**
 * Handles /clients/kb-fields response.
 *
 * @param {!Object} response
 * @private
 */
GlobExpressionFormController.prototype.onGetFields_ = function(response) {
  var fieldsNames = [];
  angular.forEach(response['data']['items'], function(field) {
    fieldsNames.push(field['value']);
  }.bind(this));

  var intervalPromise = this.interval_(function() {
    var inputBox = $(this.element_).find('input');
    if (inputBox) {
      // TODO(user): convert completer into a proper Angular directive.
      grr.glob_completer.Completer(inputBox, fieldsNames);

      this.interval_.cancel(intervalPromise);
    }
  }.bind(this), 500, 10);
};


/**
 * GlobExpressionFormDirective renders GlobExpression values.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.globExpressionFormDirective.GlobExpressionFormDirective =
    function() {
  return {
    restrict: 'E',
    scope: {
      value: '=',
      metadata: '='
    },
    templateUrl: '/static/angular-components/forms/glob-expression-form.html',
    controller: GlobExpressionFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.globExpressionFormDirective.GlobExpressionFormDirective
    .directive_name = 'grrFormGlobExpression';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.forms.globExpressionFormDirective.GlobExpressionFormDirective
    .semantic_type = 'GlobExpression';


});
