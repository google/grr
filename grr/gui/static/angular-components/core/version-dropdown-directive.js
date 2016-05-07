'use strict';

goog.provide('grrUi.core.versionDropdownDirective.VersionDropdownController');
goog.provide('grrUi.core.versionDropdownDirective.VersionDropdownDirective');


goog.scope(function() {

var REFRESH_VERSIONS_EVENT = "RefreshVersionsEvent";


/**
 * Controller for VersionDropdownDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.core.versionDropdownDirective.VersionDropdownController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Array} */
  this.versions;

  /** @type {?string} */
  this.version;

  /** @private {boolean} */
  this.updateInProgress_ = false;

  this.scope_.$watch('url', this.onDirectiveArgumentsChange_.bind(this));
  this.scope_.$watch('version', this.onScopeVersionChange_.bind(this));
  this.scope_.$watch('controller.version', this.onControllerVersionChange_.bind(this));

  this.scope_.$on(REFRESH_VERSIONS_EVENT, this.fetchVersions_.bind(this));
};

var VersionDropdownController =
    grrUi.core.versionDropdownDirective.VersionDropdownController;


/**
 * Handles changes of clientId binding.
 *
 * @private
 */
VersionDropdownController.prototype.onDirectiveArgumentsChange_ = function() {
  this.fetchVersions_();
};

/**
 * Fetches the versions.
 *
 * @private
 */
VersionDropdownController.prototype.fetchVersions_ = function() {
  var url = this.scope_['url'];
  var responseField = this.scope_['responseField'] || 'times';

  if (angular.isDefined(url)) {
    this.updateInProgress_ = true;
    this.grrApiService_.get(url).then(function success(response) {
      this.versions = response['data'][responseField];
      this.updateInProgress_ = false;
    }.bind(this), function failure(response) {
      this.updateInProgress_ = false;
    }.bind(this));
  }
};

/**
 * Handles changes to the scope version.
 *
 * @private
 */
VersionDropdownController.prototype.onScopeVersionChange_ = function() {
  // To use <options> with ng-repeat, we need to operate on string values within this directive.
  this.version = this.scope_['version'] ? this.scope_['version'].toString() : null;
};

/**
 * Handles changes to the controller version.
 *
 * @private
 */
VersionDropdownController.prototype.onControllerVersionChange_ = function() {
  // Since we cannot use ng-options, we need to convert the string selection to a number.
  this.scope_['version'] = this.version ? parseInt(this.version, 10) : null;
};

/**
 * Checks whether a version is the currently selected one.
 *
 * @param {number} value The number representation of a version.
 * @return {boolean} True if the latest item is selected, false otherwise.
 * @export
 */
VersionDropdownController.prototype.isSelected = function(value) {
  return value === parseInt(this.version, 10);
};

/**
 * Checks whether the latest item is selected or not.
 *
 * @return {boolean} True if the latest item is selected, false otherwise.
 * @export
 */
VersionDropdownController.prototype.isLatestSelected = function() {
  if (this.updateInProgress_){
    return true; // As we do not know about the elements that will be returned,
                 // we assume we have the latest version.
  }
  return !this.versions || this.versions.length === 0 || !this.scope_['version']
      || this.scope_['version'] === this.versions[0].value;
};

/**
 * VersionDropdownDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.core.versionDropdownDirective.VersionDropdownDirective = function() {
  return {
    restrict: 'E',
    scope: {
      url: '=',
      version: '=',
      responseField: '@'
    },
    templateUrl: '/static/angular-components/core/version-dropdown.html',
    controller: VersionDropdownController,
    controllerAs: 'controller'
  };
};

/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.core.versionDropdownDirective.VersionDropdownDirective.directive_name =
    'grrVersionDropdown';

grrUi.core.versionDropdownDirective.VersionDropdownDirective.refresh_versions_event =
    REFRESH_VERSIONS_EVENT;

});  // goog.scope
