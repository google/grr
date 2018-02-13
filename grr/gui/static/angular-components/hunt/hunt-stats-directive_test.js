'use strict';

goog.module('grrUi.hunt.huntStatsDirectiveTest');

const {huntModule} = goog.require('grrUi.hunt.hunt');
const {testsModule} = goog.require('grrUi.tests');


describe('hunt stats directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;


  beforeEach(module('/static/angular-components/hunt/hunt-stats.html'));
  beforeEach(module(huntModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
  }));

  const render = (huntId) => {
    $rootScope.huntId = huntId;

    const template = '<grr-hunt-stats hunt-id="huntId" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows user cpu usage histogram', () => {
    const statsResponse = {
      stats: {
        type: 'ClientResourcesStats',
        value: {
          user_cpu_stats: {
            type: 'RunningStats',
            value: {
              histogram: {
                type: 'StatsHistogram',
                value: {
                  bins: [
                    {
                      type: 'StatsHistogramBin',
                      value: {
                        num: {
                          type: 'long',
                          value: 10.55,
                        },
                        range_max_value: {
                          type: 'float',
                          value: 16.55,
                        },
                      },
                    },
                    {
                      type: 'StatsHistogramBin',
                      value: {
                        num: {
                          type: 'long',
                          value: 5.55,
                        },
                        range_max_value: {
                          type: 'float',
                          value: 32768.55,
                        },
                      },
                    }
                  ],
                },
              },
            },
          },
        },
      },
    };

    // Mock $.plot.
    $.plot = jasmine.createSpy('$.plot spy')
                 .and.callFake((element, series, options) => {
                   expect(element.hasClass('user-cpu-histogram')).toBeTruthy();
                   expect(series[0].data.length).toEqual(2);
                   expect(series[0].data[0]).toEqual([0, 10.55]);
                   expect(series[0].data[1]).toEqual([1, 5.55]);
                   expect(options.xaxis.ticks).toEqual([
                     [0.5, '16.6'], [1.5, '32768.6']
                   ]);
                 });

    const deferred = $q.defer();
    deferred.resolve({ data: statsResponse });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    render('H:12345678');
    expect(grrApiService.get).toHaveBeenCalledWith('/hunts/H:12345678/stats');
    expect($.plot).toHaveBeenCalled();
  });

  it('shows system cpu usage histogram', () => {
    const statsResponse = {
      stats: {
        type: 'ClientResourcesStats',
        value: {
          system_cpu_stats: {
            type: 'RunningStats',
            value: {
              histogram: {
                type: 'StatsHistogram',
                value: {
                  bins: [
                    {
                      type: 'StatsHistogramBin',
                      value: {
                        num: {
                          type: 'long',
                          value: 10.55,
                        },
                        range_max_value: {
                          type: 'float',
                          value: 16.55,
                        },
                      },
                    },
                    {
                      type: 'StatsHistogramBin',
                      value: {
                        num: {
                          type: 'long',
                          value: 5.55,
                        },
                        range_max_value: {
                          type: 'float',
                          value: 32768.55,
                        },
                      },
                    }
                  ],
                },
              },
            },
          },
        },
      },
    };

    // Mock $.plot.
    $.plot =
        jasmine.createSpy('$.plot spy')
            .and.callFake((element, series, options) => {
              expect(element.hasClass('system-cpu-histogram')).toBeTruthy();
              expect(series[0].data.length).toEqual(2);
              expect(series[0].data[0]).toEqual([0, 10.55]);
              expect(series[0].data[1]).toEqual([1, 5.55]);
              expect(options.xaxis.ticks).toEqual([
                [0.5, '16.6'], [1.5, '32768.6']
              ]);
            });

    const deferred = $q.defer();
    deferred.resolve({ data: statsResponse });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    render('H:12345678');
    expect(grrApiService.get).toHaveBeenCalledWith('/hunts/H:12345678/stats');
    expect($.plot).toHaveBeenCalled();
  });

  it('shows network bytes histogram with correct values and xaxis labels',
     () => {
       const statsResponse = {
         stats: {
           type: 'ClientResourcesStats',
           value: {
             network_bytes_sent_stats: {
               type: 'RunningStats',
               value: {
                 histogram: {
                   type: 'StatsHistogram',
                   value: {
                     bins: [
                       {
                         type: 'StatsHistogramBin',
                         value: {
                           num: {
                             type: 'long',
                             value: 10,
                           },
                           range_max_value: {
                             type: 'float',
                             value: 16.0,
                           },
                         },
                       },
                       {
                         type: 'StatsHistogramBin',
                         value: {
                           num: {
                             type: 'long',
                             value: 5,
                           },
                           range_max_value: {
                             type: 'float',
                             value: 32768.0,
                           },
                         },
                       }
                     ],
                   },
                 },
               },
             },
           },
         },
       };

       // Mock $.plot.
       $.plot = jasmine.createSpy('$.plot spy')
                    .and.callFake((element, series, options) => {
                      expect(element.hasClass('network-bytes-histogram'))
                          .toBeTruthy();
                      expect(series[0].data.length).toEqual(2);
                      expect(series[0].data[0]).toEqual([0, 10]);
                      expect(series[0].data[1]).toEqual([1, 5]);
                      expect(options.xaxis.ticks).toEqual([
                        [0.5, '16B'], [1.5, '32K']
                      ]);
                    });

       const deferred = $q.defer();
       deferred.resolve({data: statsResponse});
       spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

       render('H:12345678');
       expect(grrApiService.get)
           .toHaveBeenCalledWith('/hunts/H:12345678/stats');
       expect($.plot).toHaveBeenCalled();
     });
});


exports = {};
