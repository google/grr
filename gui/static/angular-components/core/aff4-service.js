'use strict';
(function() {
  var module = angular.module('grr.aff4.service', []);

  // grrAff4Service is used to fetch AFF4 objects via HTTP GET requests
  // to the server.
  var serviceImplementation = function($http) {

    var processAff4Path = function(aff4Path) {
      return aff4Path.replace(/^aff4:\//, '').replace(/\/$/, '');
    };

    this.get = function(aff4Path, params) {
      var requestParams = $.extend({}, params);
      requestParams.reason = grr.state.reason;

      // TODO(user): implement this in angular way (i.e. - make a service).
      $('#ajax_spinner').html('<img src="/static/images/ajax-loader.gif">');
      var promise = $http.get('/api/aff4/' + processAff4Path(aff4Path), {
        params: requestParams
      });
      return promise.then(function(response) {
        $('#ajax_spinner').html('');
        return response;
      });
    };
  };

  module.service('grrAff4Service', serviceImplementation);
})();
