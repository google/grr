'use strict';

goog.module('grrUi.artifact.artifactDescriptorsService');
goog.module.declareLegacyNamespace();



/**
 * Service for querying artifact descriptors.
 *
 * @param {!angular.$q} $q
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 * @export
 */
exports.ArtifactDescriptorsService = function($q, grrApiService) {
  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {angular.$q.Promise} */
  this.fillCachePromise_;

  /** @private {Object<string, Object>} */
  this.descriptorsCache_;
};

var ArtifactDescriptorsService = exports.ArtifactDescriptorsService;


/**
 * Fills the descriptors cache (if needed) by fetching list of artifacts from
 * the server.
 *
 * @return {!angular.$q.Promise} Promise that will get resolved when the cache
 *     is filled.
 * @private
 */
ArtifactDescriptorsService.prototype.fillCacheIfNeeded_ = function() {
  if (this.fillCachePromise_) {
    return this.fillCachePromise_;
  }

  var deferred = this.q_.defer();

  if (!angular.isObject(this.descriptorsCache_)) {
    this.grrApiService_.get('/artifacts').then(
        function success(response) {
          this.descriptorsCache_ = {};
          angular.forEach(response['data']['items'], function(descriptor) {
            var name =
                descriptor['value']['artifact']['value']['name']['value'];
            this.descriptorsCache_[name] = descriptor;
          }.bind(this));

          deferred.resolve();
        }.bind(this),
        function failure(response) {
          deferred.reject(response['data']['message']);
        }.bind(this)).finally(function() {
          this.fillCachePromise_ = null;
        }.bind(this));

    this.fillCachePromise_ = deferred.promise;
  } else {
    deferred.resolve();
  }

  return deferred.promise;
};


/**
 * Returns a promise resolving to a descriptors map.
 *
 * @return {!angular.$q.Promise} Promise that will resolve to a map of
 *     key => descriptor.
 * @export
 */
ArtifactDescriptorsService.prototype.listDescriptors = function() {
  return this.fillCacheIfNeeded_().then(function() {
    return angular.copy(this.descriptorsCache_);
  }.bind(this));
};


/**
 * Returns a promise resolving to a descriptor of an artifact with a given
 * name.
 *
 * @param {string} name
 * @return {!angular.$q.Promise} Promise that will resolve to a descriptor
 *     or to "undefined" if no descriptor was found for a given name.
 * @export
 */
ArtifactDescriptorsService.prototype.getDescriptorByName = function(name) {
  return this.fillCacheIfNeeded_().then(function() {
    return this.descriptorsCache_[name];
  }.bind(this));
};


/**
 * Clears the descriptors cache. Has to be called when fresh descriptors
 * data has to be fetched from the server.
 *
 * @export
 */
ArtifactDescriptorsService.prototype.clearCache = function() {
  this.descriptorsCache_ = null;
};


/**
 * Name of the service in Angular.
 */
ArtifactDescriptorsService.service_name = 'grrArtifactDescriptorsService';


