'use strict';

goog.provide('grrUi.forms.fileFinderArgsFormDirective.FileFinderArgsFormDirective');


goog.scope(function() {

/**
 * FileFinderArgsFormDirective renders FileFinderArgs values.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.fileFinderArgsFormDirective.FileFinderArgsFormDirective =
    function() {
  return {
    restrict: 'E',
    scope: {
      value: '=',
      metadata: '='
    },
    templateUrl: '/static/angular-components/forms/file-finder-args-form.html'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.fileFinderArgsFormDirective.FileFinderArgsFormDirective
    .directive_name = 'grrFormFileFinderArgs';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.forms.fileFinderArgsFormDirective.FileFinderArgsFormDirective
    .semantic_type = 'FileFinderArgs';


});
