goog.module('grrUi.forms.globExpressionFormDirective');
goog.module.declareLegacyNamespace();


/**
 * Return a list of autocomplete suggestions that include a search term,
 * delimited by %%.
 *
 * This function returns all suggestions, that include the rightmost search
 * term, stripped from %%. No suggestions are returned if the search string
 * contains no open term (thus: all opening %% have a pair of closing %%).
 *
 * @param {string} expression the expression string, containing terms
 * delimited by %% e.g. '/bar/%%fq'
 * @param {!Array<string>} entries - strings used for autocompletion
 *
 * @return {!Array<{stringWithSuggestion: string, suggestion: string}>}
 *   - suggestion {string} the raw suggestion, e.g. '%%fqdn%%'
 *   - expressionWithSuggestion {string} the expression string with an
 *     applied suggestion, e.g. '/bar/%%fqdn%%'. This string can be used
 *     to replace the full contents of the input field, if the user chooses
 *     a suggestion.
 */
exports.getSuggestions = function(expression, entries) {
  const DELIMITER = '%%';

  // no autocomplete if query or entries are empty, null, or undefined
  if (!expression || !entries) return [];

  // no autocomplete if there is no open term, which is indicated by
  // an even number of DELIMITERS, which in turn equals an odd number of parts.
  const parts = expression.split(DELIMITER);
  if (parts.length % 2 === 1) return [];

  // Remove a single, trailing % from term, to keep the autocompletion visible
  // while the user finishes writing the closing %% delimiter.
  const term = parts.pop().replace(/%$/, '');
  const prefix = parts.join(DELIMITER);

  return entries.filter(field => field.includes(term))
      .map(field => DELIMITER + field + DELIMITER)
      .map(
          field =>
              ({expressionWithSuggestion: prefix + field, suggestion: field}));
};


/**
 * Controller for GlobExpressionFormDirective.
 *
 * @constructor
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const GlobExpressionFormController = function(grrApiService, $scope) {
  this.fields = [];

  grrApiService
      .get('/clients/kb-fields')
      .then(res => res.data.items.map(item => item.value))
      .then(fields => this.fields = fields);
};


/**
 * @see exports.getSuggestions
 * @param {string} expression
 * @return {Array<{stringWithSuggestion: string, suggestion: string}>!}
 */
GlobExpressionFormController.prototype.getSuggestions = function(expression) {
  return exports.getSuggestions(expression, this.fields);
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
