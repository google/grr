'use strict';

goog.module('grrUi.docs.apiHelperService');
goog.module.declareLegacyNamespace();



/**
 * Service for registering objects by their semantic types.
 *
 * @constructor
 * @param {!angular.$q} $q
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 * @export
 */
exports.ApiHelperService = function($q, grrApiService) {
  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!Array<Object>} */
  this.helperTuples_ = [];
};
var ApiHelperService = exports.ApiHelperService;


ApiHelperService.service_name = 'grrApiHelperService';


/**
 * Clears all registered helpers.
 *
 * @export
 */
ApiHelperService.prototype.clear = function() {
  this.helperTuples_ = [];
};


/**
 * Registers helper of a given type for a given webAuthType.
 *
 * @param {string} type
 * @param {string} webAuthType
 * @param {Object} helper
 * @export
 */
ApiHelperService.prototype.registerHelper = function(type, webAuthType,
                                                     helper) {
  this.helperTuples_.push([type, webAuthType, helper]);
};


/**
 * Builds start flow request request command for a given client id and JSON
 * 'create flow' request.
 *
 * If there are multiple helpers registered, the one with a matching webAuthType
 * is used. If there are no registered helpers with a matching webAuthType,
 * the one with a null webAuthType is used.
 *
 * @param {string} webAuthType
 * @param {string} clientId
 * @param {!Object} createFlowJson
 * @return {angular.$q.Promise}
 * @private
 */
ApiHelperService.prototype.buildStartFlow_ = function(webAuthType, clientId,
                                                      createFlowJson) {
  var helpersByType = {};
  for (var i = 0; i < this.helperTuples_.length; ++i) {
    var helperTuple = this.helperTuples_[i];
    var helperType = helperTuple[0];
    var helperWebAuthType = helperTuple[1];

    // Use the helper if it's auth-type agnostic (helper[1] == null) or
    // if it has a matching webAuthType. Helpers with a matching webAuthType
    // take precedence over webAuthType-agnostic helpers.
    if (!helpersByType[helperType] && !helperWebAuthType ||
        helperWebAuthType == webAuthType) {
      helpersByType[helperType] = helperTuple;
    }
  }

  var result = {};
  var promises = [];
  angular.forEach(helpersByType, function(helperTuple, key) {
    var helperWebAuthType = helperTuple[1];
    var helper = helperTuple[2];

    var promise = helper['buildStartFlow'](clientId, createFlowJson).then(
        function(data) {
          result[key] = {
            webAuthType: helperWebAuthType,
            data: data
          };
        }.bind(this));
    promises.push(promise);
  }.bind(this));

  return this.q_.all(promises).then(function() {
    return result;
  }.bind(this));
};

/**
 * Builds start flow request command for a given client id and JSON
 * 'create flow' request. This function fetches current AdminUI.webauth_manager
 * setting and chooses an appropriate helper object to generate the command.
 *
 * If there are multiple helpers registered, the one with a matching webAuthType
 * is used. If there are no registered helpers with a matching webAuthType,
 * the one with a null webAuthType is used.
 *
 * @param {string} clientId
 * @param {!Object} createFlowJson
 * @return {angular.$q.Promise}
 * @export
 */
ApiHelperService.prototype.buildStartFlow = function(clientId, createFlowJson) {
  return this.grrApiService_.getCached('/config/AdminUI.webauth_manager').then(
      function(response) {
        var webAuthType = response['data']['value']['value'];
        return this.buildStartFlow_(webAuthType, clientId, createFlowJson);
      }.bind(this));
};


