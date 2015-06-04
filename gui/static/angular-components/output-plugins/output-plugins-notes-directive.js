'use strict';

goog.provide('grrUi.outputPlugins.outputPluginsNotesDirective.OutputPluginsNotesController');
goog.provide('grrUi.outputPlugins.outputPluginsNotesDirective.OutputPluginsNotesDirective');


goog.scope(function() {

/**
 * Controller for OutputPluginsNotesDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.aff4Service.Aff4Service} grrAff4Service
 * @ngInject
 */
grrUi.outputPlugins.outputPluginsNotesDirective.OutputPluginsNotesController =
    function($scope, grrAff4Service) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.aff4Service.Aff4Service} */
  this.grrAff4Service_ = grrAff4Service;

  /** @export {?string} */
  this.error;

  this.scope_.$watch('metadataUrn', this.onMetadataUrnChange_.bind(this));
};
var OutputPluginsNotesController =
    grrUi.outputPlugins.outputPluginsNotesDirective
    .OutputPluginsNotesController;


/**
 * Handles changes in metadata urn.
 *
 * @param {?string} newValue New metadata urn.
 * @private
 */
OutputPluginsNotesController.prototype.onMetadataUrnChange_ = function(
    newValue) {
  if (angular.isDefined(newValue)) {
    this.grrAff4Service_.get(
        newValue, {'AFF4Object.type_info': 'WITH_TYPES_AND_METADATA'}).then(
            function success(response) {
              this.states = response.data['attributes'][
                'aff4:output_plugins_state'];
            }.bind(this),
            function failure(response) {
              this.error = response.data.message;
            }.bind(this));
  }
};


/**
 * Directive for displaying notes for output plugins of a flow or hunt.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.outputPlugins.outputPluginsNotesDirective.OutputPluginsNotesDirective =
    function() {
  return {
    scope: {
      metadataUrn: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/output-plugins/' +
        'output-plugins-notes.html',
    controller: OutputPluginsNotesController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.outputPlugins.outputPluginsNotesDirective.OutputPluginsNotesDirective
    .directive_name = 'grrOutputPluginsNotes';

});  // goog.scope
