goog.module('grrUi.core.reflectionService');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');



/**
 * Service for querying reflection data about RDFValues (and, in the future -
 * AFF4Objects).
 * @export
 * @unrestricted
 */
exports.ReflectionService = class {
  /**
   * @param {!angular.$q} $q
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($q, grrApiService) {
    /** @private {!angular.$q} */
    this.q_ = $q;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {Object.<string, Object>} */
    this.descriptorsCache_;

    /** @private {Array.<Object>} */
    this.requestsQueue_ = [];
  }

  /**
   * Processes requests that were queued while descriptors were being fetched.
   *
   * @private
   */
  processRequestsQueue_() {
    angular.forEach(this.requestsQueue_, function(request) {
      const result =
          this.getRDFValueDescriptorFromCache_(request[1], request[2]);
      request[0].resolve(result);
    }.bind(this));

    this.requestsQueue_ = [];
  }

  /**
   * Returns descriptor of a given RDFValue (optionally with descriptors of all
   * nested fields).
   *
   * @param {string} valueType RDFValue type.
   * @param {boolean=} opt_withDeps If true, also return descriptors of all
   *     nested
   *                                fields.
   * @return {Object} If opt_withDeps is true, returns a dictionary of
   *                  "type -> descriptor" pairs. If opt_withDeps is false,
   *                   returns a requested descriptor.
   * @private
   */
  getRDFValueDescriptorFromCache_(valueType, opt_withDeps) {
    if (!opt_withDeps) {
      return this.descriptorsCache_[valueType];
    } else {
      const results = {};

      const fillInResult = function(type) {
        if (angular.isDefined(results[type])) {
          return;
        }

        const descriptor = this.descriptorsCache_[type];
        results[type] = descriptor;

        angular.forEach(descriptor['fields'], function(fieldDescriptor) {
          if (angular.isDefined(fieldDescriptor['type'])) {
            fillInResult(fieldDescriptor['type']);
          }
        });
      }.bind(this);

      fillInResult(valueType);
      return results;
    }
  }

  /**
   * Fills in descriptors for primitive types.
   * This used to be done in the API handler, but we moved it here in
   * preparation for the rdf migration of such handler. Primitive values are not
   * returned by the API handler anymore.
   * @private
   */
  fillPrimitiveDescriptors_() {
    const primitive_types =
        ['bool', 'int', 'float', 'str', 'bytes', 'unicode', 'long'];
    angular.forEach(primitive_types, function(type_name) {
      this.descriptorsCache_[type_name] = {
        'name': type_name,
        'mro': [type_name, 'object'],
        'kind': 'primitive',
      };
      if (type_name === 'bool') {
        this.descriptorsCache_[type_name]['mro'].push('int');
      }
      if (type_name === 'float') {
        this.descriptorsCache_[type_name]['default'] = {
          type: 'float',
          value: 0
        };
      }
    }.bind(this));
  }

  /**
   * Returns descriptor of a given RDFValue (optionally with descriptors of all
   * nested fields).
   *
   * @param {string} valueType RDFValue type.
   * @param {boolean=} opt_withDeps If true, also return descriptors of all
   *     nested
   *                                fields.
   * @return {!angular.$q.Promise} Promise that resolves to result. If
   *                               opt_withDeps is true, it will resolve to a
   *                               dictionary of "type -> descriptor" pairs. If
   *                               opt_withDeps is false, it will just return
   *                               a requested descriptor.
   */
  getRDFValueDescriptor(valueType, opt_withDeps) {
    const deferred = this.q_.defer();

    if (angular.isDefined(this.descriptorsCache_)) {
      const result =
          this.getRDFValueDescriptorFromCache_(valueType, opt_withDeps);
      deferred.resolve(result);
      return deferred.promise;
    } else {
      if (this.requestsQueue_.length === 0) {
        const apiPromise = this.grrApiService_.get('reflection/rdfvalue/all');
        apiPromise.then(function(response) {
          this.descriptorsCache_ = {};
          angular.forEach(response['data']['items'], function(item) {
            this.descriptorsCache_[item['name']] = item;
          }.bind(this));
          this.fillPrimitiveDescriptors_();

          return this.processRequestsQueue_();
        }.bind(this));
      }
      this.requestsQueue_.push([deferred, valueType, opt_withDeps]);
      return deferred.promise;
    }
  }
};
const ReflectionService = exports.ReflectionService;


/**
 * Name of the service in Angular.
 */
ReflectionService.service_name = 'grrReflectionService';
