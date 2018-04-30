'use strict';

goog.module('grrUi.stats.serverLoadDirectiveTest');

const {ServerLoadIndicatorService} = goog.require('grrUi.stats.serverLoadDirective');
const {statsModule} = goog.require('grrUi.stats.stats');


describe('server load indicator service', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiServiceMock;


  beforeEach(module(statsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');

    grrApiServiceMock = {get: function() {}};
  }));

  describe('ratio health indicators', () => {
    const getService =
        ((numeratorPath, numeratorResponse, denominatorPath,
          denominatorResponse) => {
          let service;

          inject(($injector) => {
            service = $injector.instantiate(ServerLoadIndicatorService, {
              '$q': $q,
              'grrApiService': grrApiServiceMock,
            });
          });

          const deferredNumerator = $q.defer();
          deferredNumerator.resolve(numeratorResponse);

          const deferredDenominator = $q.defer();
          deferredDenominator.resolve(denominatorResponse);

          spyOn(grrApiServiceMock, 'get').and.callFake((path) => {
            if (path === 'stats/store/FRONTEND/metrics/metric1') {
              return deferredNumerator.promise;
            } else if (path === 'stats/store/FRONTEND/metrics/metric2') {
              return deferredDenominator.promise;
            } else {
              throw new Error(`Unexpected path: ${path}`);
            }
          });

          $rootScope.$apply();

          return service;
        });

    it('sets unknown status when no data received', () => {
      const service = getService(
          'FRONTEND/metrics/metric1', {
            data: {
              metric_name: 'metric1',
              data_points: [],
            },
          },
          'FRONTEND/metrics/metric2', {
            data: {
              metric_name: 'metric2',
              data_points: [],
            },
          });

      const status =
          service.fetchRatioIndicator('FRONTEND', 'metric1', 'metric2', 1.5, 3);
      let resolvedStatus;
      status.then((value) => {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('unknown');
    });

    it('sets unknown when denominator is zero', () => {
      const service = getService(
          'FRONTEND/metrics/metric1', {
            data: {
              metric_name: 'metric1',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              data_points: [[0, 1]],
            },
          },
          'FRONTEND/metrics/metric2', {
            data: {
              metric_name: 'metric2',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              data_points: [[0, 0]],
            },
          });

      const status =
          service.fetchRatioIndicator('FRONTEND', 'metric1', 'metric2', 1.5, 3);
      let resolvedStatus;
      status.then((value) => {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('unknown');
    });

    it('sets warning status when ratio level is above threshold', () => {
      const service = getService(
          'FRONTEND/metrics/metric1', {
            data: {
              metric_name: 'metric1',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              data_points: [[0, 4]],
            },
          },
          'FRONTEND/metrics/metric2', {
            data: {
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              metric_name: 'metric2',
              data_points: [[0, 2]],
            },
          });

      const status =
          service.fetchRatioIndicator('FRONTEND', 'metric1', 'metric2', 1.5, 3);
      let resolvedStatus;
      status.then((value) => {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('warning');
    });

    it('sets warning status when mean ratio is above threshold', () => {
      const service = getService(
          'FRONTEND/metrics/metric1', {
            data: {
              metric_name: 'metric1',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              data_points: [[0, 3], [10, 5]],
            },
          },
          'FRONTEND/metrics/metric2', {
            data: {
              metric_name: 'metric2',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              data_points: [[0, 1], [10, 3]],
            },
          });

      const status =
          service.fetchRatioIndicator('FRONTEND', 'metric1', 'metric2', 1.5, 3);
      let resolvedStatus;
      status.then((value) => {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('warning');
    });

    it('sets danger status when ratio level is above threshold', () => {
      const service = getService(
          'FRONTEND/metrics/metric1', {
            data: {
              metric_name: 'metric1',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              data_points: [[0, 7]],
            },
          },
          'FRONTEND/metrics/metric2', {
            data: {
              metric_name: 'metric2',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              data_points: [[0, 2]],
            },
          });

      const status =
          service.fetchRatioIndicator('FRONTEND', 'metric1', 'metric2', 1.5, 3);
      let resolvedStatus;
      status.then((value) => {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('danger');
    });

    it('sets normal status when ratio level is below threshold', () => {
      const service = getService(
          'FRONTEND/metrics/metric1', {
            data: {
              metric_name: 'metric1',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              data_points: [[0, 2]],
            },
          },
          'FRONTEND/metrics/metric2', {
            data: {
              metric_name: 'metric2',
              // First value in evey time series itme is a timestamp,
              // second is the metric value.
              data_points: [[0, 2]],
            },
          });

      const status =
          service.fetchRatioIndicator('FRONTEND', 'metric1', 'metric2', 1.5, 3);
      let resolvedStatus;
      status.then((value) => {
        resolvedStatus = value;
      });

      $rootScope.$apply();
      expect(resolvedStatus).toBeDefined();
      expect(resolvedStatus).toEqual('normal');
    });
  });
});  // goog.scope


exports = {};
