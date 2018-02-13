'use strict';

goog.module('grrUi.semantic.rekall.rekallJsonDirective');
goog.module.declareLegacyNamespace();

const {cropRekallJson, stackRekallTables} = goog.require('grrUi.semantic.rekall.utils');



/**
 * Controller for RekallJsonDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
const RekallJsonController =
    function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Object} */
  this.parsedJson;

  /** @type {string} */
  this.error = '';

  /** @type {string} */
  this.jsonContextStr;

  /** @type {string} */
  this.compressedJsonStr;

  /** @type {*} */
  this.state;

  /** @type {boolean} */
  this.renderIncomplete = true;

  this.scope_.$watchGroup(['jsonContextMessages', 'compressedJsonMessages'],
                          this.onScopeChange_.bind(this));
};


/**
 * @const {number} Maximum number of bytes to render without showing a link.
 */
var FIRST_RENDER_LIMIT = 1024;


/**
 * Handler for the click events.
 *
 * @param {?} e An event object.
 */
RekallJsonController.prototype.onClick = function(e) {
  // onClick event should not be handled by
  // anything other than this, otherwise the click
  // could be interpreted in the wrong way,
  // e.g. page could be redirected.
  e.stopPropagation();

  this.render_();
};

/**
 * @param {number=} opt_renderLimit The maximum size of the data to be rendered.
 * @private
 */
RekallJsonController.prototype.render_ = function(opt_renderLimit) {
  /** @type {number} */
  var renderLimit = opt_renderLimit || Infinity;

  if (this.jsonContextStr.length + this.compressedJsonStr.length <=
      renderLimit) {
    this.renderIncomplete = false;
  }

  try {
    this.parsedJson =
        JSON.parse(cropRekallJson(this.jsonContextStr, renderLimit))
            .concat(JSON.parse(cropRekallJson(
                this.compressedJsonStr,
                renderLimit - this.jsonContextStr.length)));
  }
  catch (err) {
    this.error = 'error: ' + err.message + ', in:' + this.jsonContextStr +
                 ', ' + this.compressedJsonStr;

    return;
  }

  this.state = stackRekallTables(this.parsedJson);
};

/**
 * Handles changes of scope attributes.
 * @private
 */
RekallJsonController.prototype.onScopeChange_ = function() {
  if (angular.isDefined(this.state)) {
    return;
  }

  var jsonContext = this.scope_['jsonContextMessages'];
  var compressedJson = this.scope_['compressedJsonMessages'];

  if (angular.isUndefined(jsonContext) ||
      angular.isUndefined(compressedJson)) {
    return;
  }

  this.jsonContextStr = jsonContext.value;
  this.compressedJsonStr = compressedJson.value;

  if (!angular.isString(this.jsonContextStr) ||
      !angular.isString(this.compressedJsonStr)) {
    this.error = 'Expected strings, got ' + typeof this.jsonContextStr +
                 ' and ' + typeof this.compressedJsonStr + '.';
    return;
  }

  this.render_(FIRST_RENDER_LIMIT);
};



/**
 * Directive that displays Rekall Json values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.RekallJsonDirective = function() {
  return {
    scope: {
      jsonContextMessages: '=',
      compressedJsonMessages: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/rekall/rekall-json.html',
    controller: RekallJsonController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.RekallJsonDirective.directive_name = 'grrRekallJson';
