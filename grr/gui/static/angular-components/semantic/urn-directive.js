'use strict';

goog.provide('grrUi.semantic.urnDirective.UrnController');
goog.provide('grrUi.semantic.urnDirective.UrnDirective');
goog.require('grrUi.client.virtualFileSystem.fileViewDirective.getFileId');

goog.scope(function() {


var getFileId = grrUi.client.virtualFileSystem.fileViewDirective.getFileId;


/**
 * Controller for UrnDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
grrUi.semantic.urnDirective.UrnController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?string} */
  this.plainValue;

  /** @type {?string} */
  this.hash;

  this.scope_.$watch('::value', this.onValueChange_.bind(this));
};
var UrnController = grrUi.semantic.urnDirective.UrnController;


/**
 * Regex that matches files inside the client.
 *
 * @const
 * @export
 */
grrUi.semantic.urnDirective.CLIENT_ID_RE =
    /^aff4:\/?((c|C)\.[0-9a-fA-F]{16})\//;


/**
 * Derives URL-friendly id from the urn.
 *
 * @param {string} urn Urn to derive id from.
 * @return {string} Derived id.
 * @private
 */
UrnController.prototype.deriveIdFromUrn_ = function(urn) {
  var invalidChars = /[^a-zA-Z0-9]/;

  var components = urn.split('/').slice(2);
  return getFileId(components.join('/'));
};


/**
 * Handles value changes.
 *
 * @param {?string} newValue
 * @private
 */
UrnController.prototype.onValueChange_ = function(newValue) {
  if (angular.isObject(newValue)) {
    this.plainValue = newValue.value;
  } else if (angular.isString(newValue)) {
    this.plainValue = newValue;
  } else {
    return;
  }

  var m = this.plainValue.match(grrUi.semantic.urnDirective.CLIENT_ID_RE);
  if (m) {
    var client = m[1];
    var derivedId = this.deriveIdFromUrn_(this.plainValue);

    this.hash = $.param({
      main: 'VirtualFileSystemView',
      c: client,
      tag: 'AFF4Stats',
      t: derivedId
    });
  }
};


/**
 * Handles clicks on the link.
 * @export
 */
UrnController.prototype.onClick = function() {
  grr.loadFromHash(/** @type {string} */ (this.hash));
};


/**
 * Directive that displays RDFURN values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.urnDirective.UrnDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/urn.html',
    controller: UrnController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.urnDirective.UrnDirective.directive_name =
    'grrUrn';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.urnDirective.UrnDirective.semantic_type =
    'RDFURN';


});  // goog.scope
