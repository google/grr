'use strict';

goog.provide('grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteController');
goog.provide('grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteDirective');


goog.scope(function() {

/**
 * Controller for OutputPluginNoteDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$compile} $compile
 * @param {!angular.JQLite} $element
 * @param {!grrUi.core.semanticRegistry.SemanticRegistryService}
 *     grrOutputPluginsDirectivesRegistryService
 * @ngInject
 */
grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteController =
    function($scope, $compile, $element,
             grrOutputPluginsDirectivesRegistryService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Object} */
  this.scope_.descriptor;

  /** @type {Object} */
  this.scope_.state;

  /** @private {!angular.$compile} */
  this.compile_ = $compile;

  /** @private {!angular.JQLite} */
  this.element_ = $element;

  /** @private {!grrUi.core.semanticRegistry.SemanticRegistryService} */
  this.grrOutputPluginsDirectivesRegistryService_ =
      grrOutputPluginsDirectivesRegistryService;

  this.scope_.$watchGroup(['descriptor', 'state'],
                          this.onDescriptorOrStateChange_.bind(this));
};
var OutputPluginNoteController =
    grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteController;



/**
 * Converts camelCaseStrings to dash-delimited-strings.
 *
 * @param {string} directiveName String to be converted.
 * @return {string} Converted string.
 */
OutputPluginNoteController.prototype.camelCaseToDashDelimited = function(
    directiveName) {
  return directiveName.replace(/([a-z\d])([A-Z])/g, '$1-$2').toLowerCase();
};


/**
 * Handles changes in descriptor or state.
 *
 * @private
 */
OutputPluginNoteController.prototype.onDescriptorOrStateChange_ = function() {
  if (angular.isDefined(this.scope_.descriptor) &&
      angular.isDefined(this.scope_.state)) {

    var pluginName = this.scope_.descriptor['value']['plugin_name']['value'];
    var directive = this.grrOutputPluginsDirectivesRegistryService_
        .findDirectiveForMro([pluginName]);

    if (angular.isDefined(directive)) {
      var element = angular.element('<span />');
      element.html('<' +
        this.camelCaseToDashDelimited(directive.directive_name) +
        ' descriptor="descriptor" state="state" />');

      var template = this.compile_(element);
      template(this.scope_, function(cloned, opt_scope) {
        this.element_.html('');
        this.element_.append(cloned);
      }.bind(this));
    } else {
      this.element_.html('');
    }

  }
};

/**
 * Directive for displaying notes for output plugins of a flow or hunt.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteDirective =
    function() {
  return {
    scope: {
      descriptor: '=',
      state: '='
    },
    restrict: 'E',
    controller: OutputPluginNoteController,
    controllerAs: 'controller'
  };
};

/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteDirective
    .directive_name = 'grrOutputPluginNote';


});
