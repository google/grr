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

  // When either a URL or a current version changes, refresh the versions list.
  this.scope_.$watchGroup(['url', 'version'], this.fetchVersions_.bind(this));

  this.scope_.$watch('controller.version', this.onControllerVersionChange_.bind(this));

  this.scope_.$on(REFRESH_VERSIONS_EVENT, this.fetchVersions_.bind(this));
};

var VersionDropdownController =
    grrUi.core.versionDropdownDirective.VersionDropdownController;


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

      // If no versions were fetched from the server, do nothing and
      // do not change the model (by changing this.version).
      if (!this.versions.length) {
        return;
      }

      // If version is specified, ensure it's present in the list.
      if (this.scope_['version']) {
        this.versions.push({
          value: this.scope_['version'],
          type: 'RDFDatetime'
        });

        // Sort the array by value in the descending order.
        this.versions.sort(function(v1, v2) {
          if (v1['value'] < v2['value']) {
            return 1;
          } else if (v1['value'] == v2['value']) {
            return 0;
          } else {
            return -1;
          }
        }.bind(this));
        // Remove duplicates from a sorted array.
        this.versions = this.versions.filter(function(value, index, arr) {
          if (index == 0) {
            return true;
          } else {
            return value['value'] != arr[index - 1]['value'];
          }
        }.bind(this));

        this.version = this.scope_['version'].toString();
      } else {
        this.version = 'HEAD';
      }

    }.bind(this)).finally(function() {
      this.updateInProgress_ = false;
    }.bind(this));
  }
};

/**
 * Handles changes to the controller version.
 *
 * @private
 */
VersionDropdownController.prototype.onControllerVersionChange_ = function() {
  if (angular.isUndefined(this.version)) {
    return;
  }

  // Since we cannot use ng-options, we need to convert the string selection to a number.
  if (this.version == 'HEAD') {
    this.scope_['version'] = undefined;
  } else {
    this.scope_['version'] = parseInt(this.version, 10);
  }
};

/**
 * Checks whether a version is the currently selected one.
 *
 * @param {number} value The number representation of a version.
 * @return {boolean} True if the latest item is selected, false otherwise.
 * @export
 */
VersionDropdownController.prototype.isSelected = function(value) {
  if (value == 'HEAD') {
    return this.version == value;
  } else {
    return parseInt(this.version, 10) == value;
  }
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

  if (this.version == 'HEAD') {
    return true;
  }

  return !this.versions || this.versions.length === 0 || !this.scope_['version']
      || this.version === this.versions[0].value.toString();
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

/**
 * "Refresh versions" event name.
 * @const
 */
grrUi.core.versionDropdownDirective.VersionDropdownDirective.REFRESH_VERSIONS_EVENT =
    REFRESH_VERSIONS_EVENT;

});  // goog.scope
