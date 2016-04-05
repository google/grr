'use strict';

goog.require('grrUi.stats.module');
goog.require('grrUi.stats.serverLoadDirective.ServerLoadIndicatorService');

describe('server load indicator service', function() {
  var $q, $compile, $rootScope, grrApiServiceMock;

  beforeEach(module(grrUi.stats.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');

    grrApiServiceMock = {get: function() {}};
  }));

  describe('ratio health indicators', function() {
    var getService = function(numeratorPath, numeratorResponse,
                              denominatorPath, denominatorResponse) {
      var service;

      inject(function($injector) {
        service = $injector.instantiate(
            grrUi.stats.serverLoadDirective.ServerLoadIndicatorService,
            {
              '$q': $q,
              'grrApiService': grrApiServiceMock
            });
      });

      var deferredNumerator = $q.defer();
      deferredNumerator.resolve(numeratorResponse);

      var deferredDenominator = $q.defer();
      deferredDenominator.resolve(denominatorResponse);

      spyOn(grrApiServiceMock, 'get').and.callFake(function(path) {
        if (path === 'stats/store/FRONTEND/metrics/metric1') {
          return deferredNumerator.promise;
        } else if (path === 'stats/store/FRONTEND/metrics/metric2') {
          return deferredDenominator.promise;
        } else {
          throw new Error('Unexpected path: ' + path);
        }
      });

      $rootScope.$apply();

      return service;
    };

    it('sets unknown status when no data received', function() {
      var service = getService(
          'FRONTEND/metrics/metric1',
          {
            data: {
              metric_name: 'metric1',
              timeseries: []
            }
          },
          'FRONTEND/metrics/metric2',
          {
            data: {
              metric_name: 'metric2',
              timeseries: []
            }
          });

      var status = service.fetchRatioIndicator(
          'FRONTEND', 'metric1', 'metric2', 1.5, 3);
      var resolvedStatus;
      status.then(function(value) {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('unknown');
    });

    it('sets unknown when denominator is zero', function() {
      var service = getService(
          'FRONTEND/metrics/metric1',
          {
            data: {
              metric_name: 'metric1',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              timeseries: [[0, 1]]
            }
          },
          'FRONTEND/metrics/metric2',
          {
            data: {
              metric_name: 'metric2',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              timeseries: [[0, 0]]
            }
          });

      var status = service.fetchRatioIndicator(
          'FRONTEND', 'metric1', 'metric2', 1.5, 3);
      var resolvedStatus;
      status.then(function(value) {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('unknown');
    });

    it('sets warning status when ratio level is above threshold', function() {
      var service = getService(
          'FRONTEND/metrics/metric1',
          {
            data: {
              metric_name: 'metric1',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              timeseries: [[0, 4]]
            }
          },
          'FRONTEND/metrics/metric2',
          {
            data: {
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              metric_name: 'metric2',
              timeseries: [[0, 2]]
            }
          });

      var status = service.fetchRatioIndicator(
          'FRONTEND', 'metric1', 'metric2', 1.5, 3);
      var resolvedStatus;
      status.then(function(value) {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('warning');
    });

    it('sets warning status when mean ratio is above threshold', function() {
      var service = getService(
          'FRONTEND/metrics/metric1',
          {
            data: {
              metric_name: 'metric1',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              timeseries: [[0, 3], [10, 5]]
            }
          },
          'FRONTEND/metrics/metric2',
          {
            data: {
              metric_name: 'metric2',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              timeseries: [[0, 1], [10, 3]]
            }
          });

      var status = service.fetchRatioIndicator(
          'FRONTEND', 'metric1', 'metric2', 1.5, 3);
      var resolvedStatus;
      status.then(function(value) {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('warning');
    });

    it('sets danger status when ratio level is above threshold', function() {
      var service = getService(
          'FRONTEND/metrics/metric1',
          {
            data: {
              metric_name: 'metric1',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              timeseries: [[0, 7]]
            }
          },
          'FRONTEND/metrics/metric2',
          {
            data: {
              metric_name: 'metric2',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              timeseries: [[0, 2]]
            }
          });

      var status = service.fetchRatioIndicator(
          'FRONTEND', 'metric1', 'metric2', 1.5, 3);
      var resolvedStatus;
      status.then(function(value) {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('danger');
    });

    it('sets normal status when ratio level is below threshold', function() {
      var service = getService(
          'FRONTEND/metrics/metric1',
          {
            data: {
              metric_name: 'metric1',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              timeseries: [[0, 2]]
            }
          },
          'FRONTEND/metrics/metric2',
          {
            data: {
              metric_name: 'metric2',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              timeseries: [[0, 2]]
            }
          });

      var status = service.fetchRatioIndicator(
          'FRONTEND', 'metric1', 'metric2', 1.5, 3);
      var resolvedStatus;
      status.then(function(value) {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('normal');
    });
  });

});  // goog.scope
