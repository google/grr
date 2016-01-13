'use strict';

goog.provide('grrUi.forms.semanticLabelFormDirective');
goog.provide('grrUi.forms.semanticLabelFormDirective.SemanticLabelFormController');
goog.provide('grrUi.forms.semanticLabelFormDirective.SemanticLabelFormDirective');
goog.scope(function() {


/**
 * Controller for SemanticLabelFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.forms.semanticLabelFormDirective.SemanticLabelFormController = function(
    $scope, grrReflectionService, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  this.labelsList = [];

  this.grrApiService_.get('/clients/labels').then(function(response) {
    this.labelsList = response['data']['items'];

    this.scope_.$watch('value', function () {
      var label_name = this.scope_['value']['value']['label_name'];
      if (angular.isUndefined(label_name)) {
        label_name = {type: 'unicode'};
      }

      if (angular.isUndefined(label_name.value) && this.labelsList.length > 0) {
        label_name.value = this.labelsList[0];
      }
    }.bind(this));
  }.bind(this));
};
var SemanticLabelFormController =
    grrUi.forms.semanticLabelFormDirective.SemanticLabelFormController;


/**
 * SemanticLabelFormDirective renders a ForemanLabelClientRule.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.semanticLabelFormDirective.SemanticLabelFormDirective = function() {
  return {
    restrict: 'E',
    scope: {
      value: '=',
      metadata: '='
    },
    templateUrl: '/static/angular-components/forms/semantic-label-form.html',
    controller: SemanticLabelFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.semanticLabelFormDirective.SemanticLabelFormDirective
    .directive_name = 'grrFormLabel';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.forms.semanticLabelFormDirective.SemanticLabelFormDirective
    .semantic_type = 'ForemanLabelClientRule';

});  // goog.scope
