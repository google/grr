goog.module('grrUi.user.approverInputDirective');
goog.module.declareLegacyNamespace();


/**
 * Controller for ApproverInputDirective.
 *
 * @constructor
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!angular.$q} $q
 * @ngInject
 */
const ApproverInputController = function(grrApiService, $q) {
  this.$q = $q;
  this.grrApiService_ = grrApiService;
};


/**
 * Load suggestions for approver usernames. This function splits the input
 * string at comma followed by optional whitespace. The rightmost match is
 * used as search query to load username suggestions from the backend.
 *
 * @param {string} input the approvers input string, containing usernames
 *     separated by comma and optional whitespace
 *
 * @return {!angular.$q.Promise<!Array<{suggestion: string, username: string}>>}
 *     array of autocomplete items.
 *     - suggestion: the suggested new input which is the concatenation of
 *       '<previously entered usernames>, <autocompl. for current username>, '
 *     - username: the suggested username for the current query string
 */
ApproverInputController.prototype.loadApproverSuggestions = function(input) {
  // Do not show autocomplete for empty input string.
  if (!input) return this.$q.resolve([]);

  // Split input into a prefix (commas and spaces preserved) and search term.
  const matches = input.match(/^(.*?)([^,\s]+)$/);

  // Do not show autocomplete, if current search term is empty,
  // e.g. last character is ','.
  if (!matches) return this.$q.resolve([]);

  const [, prefix, usernameQuery] = matches;

  // Do not suggest previously entered usernames.
  const ignore = prefix.split(/\s*,\s*/);

  return this.grrApiService_
      .get('/users/approver-suggestions', {username_query: usernameQuery})
      .then(
          (res) => res.data['suggestions']
              .map((suggestion) => suggestion.value.username.value)
              .filter((username) => !ignore.includes(username))
              .map((username) => ({
                suggestion: prefix + username + ', ',
                username: username,
              })));
};


/**
 * ApproverInputDirective renders Approver values.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.ApproverInputDirective = function() {
  return {
    restrict: 'E',
    scope: {
      model: "=ngModel",
    },
    templateUrl: '/static/angular-components/user/approver-input.html',
    controller: ApproverInputController,
    controllerAs: 'controller',
  };
};


/**
 * Name of the directive in Angular.
 *
 * @export @const
 */
exports.ApproverInputDirective.directive_name = 'grrApproverInput';
