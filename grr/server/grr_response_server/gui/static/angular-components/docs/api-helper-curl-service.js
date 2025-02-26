goog.module('grrUi.docs.apiHelperCurlService');
goog.module.declareLegacyNamespace();



/**
 * Service for registering objects by their semantic types.
 * @export
 * @unrestricted
 */
exports.ApiHelperCurlService = class {
  /**
   * @param {!angular.$q} $q
   * @param {!angular.$window} $window
   * @ngInject
   */
  constructor($q, $window) {
    /** @private {!angular.$q} */
    this.q_ = $q;

    /** @private {!angular.$window} */
    this.window_ = $window;
  }

  /**
   * Builds a CURL command to start a flow on a given client.
   *
   * @param {string} clientId
   * @param {!Object} createFlowJson
   * @return {!angular.$q.Promise}
   * @export
   */
  buildStartFlow(clientId, createFlowJson) {
    const deferred = this.q_.defer();

    let result = 'CSRFTOKEN=`curl ' + this.window_.location.origin +
        ' -o /dev/null -s -c - | grep csrftoken  | cut -f 7`; \\\n\t' +
        'curl -X POST -H "Content-Type: application/json" ' +
        '-H "X-CSRFToken: $CSRFTOKEN" \\\n\t' + this.window_.location.origin +
        '/api/v2/clients/' + clientId + '/flows -d @- << EOF\n';

    result += JSON.stringify(createFlowJson, null, 2);
    result += '\nEOF';

    deferred.resolve(result);
    return deferred.promise;
  }
};
const ApiHelperCurlService = exports.ApiHelperCurlService;


ApiHelperCurlService.service_name = 'grrApiHelperCurlService';
