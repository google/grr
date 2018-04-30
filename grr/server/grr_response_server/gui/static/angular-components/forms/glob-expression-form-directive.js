'use strict';

goog.module('grrUi.forms.globExpressionFormDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for GlobExpressionFormDirective.
 *
 * @constructor
 * @param {!angular.jQuery} $element
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const GlobExpressionFormController = function(
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


/**
 * A filter function which matches the start of the completion list.
 *
 * @param {Array} completions the completion list
 * @param {string} term is the term to match.
 *
 * @return {Array} a list of matches.
 * @private
 */
GlobExpressionFormController.prototype.completionFilter_ = function(
    completions, term) {
  var matcher = new RegExp('^' +
      $['ui']['autocomplete']['escapeRegex'](term), 'i');
  return $['grep'](completions, function(value) {
    return matcher.test(value.label || value.value || value);
  });
};

/**
 * Build a completer on top of a text input.
 *
 * @param {string|Element|null|jQuery} element is the DOM id of the text input
 *     field or the DOM element itself.
 * @param {Array} completions are possible completions for %% sequences.
 *
 * @private
 */
GlobExpressionFormController.prototype.buildCompleter_ = function(
    element, completions) {
  if (angular.isString(element)) {
    element = $('#' + element);
  }

  // TODO(user): rewrite with Angular, drop jQuery UI dependency.
  var self = this;
  element.bind('keydown', function(event) {
    if (event.keyCode === $['ui']['keyCode']['TAB'] &&
        $(this).data('ui-autocomplete')['menu']['active']) {
      event.preventDefault();
    }
  })['autocomplete']({
    minLength: 0,
    source: function(request, response) {
      var terms = request['term'].split(/%%/);
      if (terms.length % 2) {
        response([]);
      } else {
        response(self.completionFilter_(completions, terms.pop()));
      }
    },
    focus: function() {
      // prevent value inserted on focus
      return false;
    },
    select: function(event, ui) {
      var terms = this.value.split(/%%/);
      // remove the current input
      terms.pop();

      // add the selected item
      terms.push(ui.item.value);
      terms.push('');

      this.value = terms.join('%%');
      // Angular code has to be notificed of the change.
      $(this).change();
      return false;
    }
  }).wrap('<abbr title="Type %% to open a list of possible completions."/>');
};


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
      this.buildCompleter_(inputBox, fieldsNames);

      this.interval_.cancel(intervalPromise);
    }
  }.bind(this), 500, 10);
};


/**
 * GlobExpressionFormDirective renders GlobExpression values.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.GlobExpressionFormDirective = function() {
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
exports.GlobExpressionFormDirective.directive_name = 'grrFormGlobExpression';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.GlobExpressionFormDirective.semantic_type = 'GlobExpression';
