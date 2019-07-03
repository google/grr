goog.module('grrUi.hunt.huntStatsDirectiveTest');
goog.setTestOnly();

const {huntModule} = goog.require('grrUi.hunt.hunt');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('hunt stats directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;


  beforeEach(module('/static/angular-components/hunt/hunt-stats.html'));
  beforeEach(module(huntModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrComparisonChart');

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
                    },
                    {
                      type: 'StatsHistogramBin',
                      value: {
                        num: {
                          type: 'long',
                          value: 9.55,
                        },
                        range_max_value: {
                          type: 'float',
                          value: 62768.55,
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

    const deferred = $q.defer();
    deferred.resolve({ data: statsResponse });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    const element = render('H:12345678');
    const directive = element.find('grr-comparison-chart:nth(0)');
    const directiveTypedData =
          directive.scope().$eval(directive.attr('typed-data'));
    expect(directiveTypedData['value']).toEqual({
      data: [
        {value: {label: {value: '< 16.6s'}, x: {value: 10.55}}},
        {value: {label: {value: '< 32768.6s'}, x: {value: 5.55}}},
        // Max range value of the last bucket should be ignored and
        // the one of the one-before-the-last bucket should be used.
        {value: {label: {value: '> 32768.6s'}, x: {value: 9.55}}},
      ]
    });
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
                    },
                    {
                      type: 'StatsHistogramBin',
                      value: {
                        num: {
                          type: 'long',
                          value: 9.55,
                        },
                        range_max_value: {
                          type: 'float',
                          value: 62768.55,
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

    const deferred = $q.defer();
    deferred.resolve({ data: statsResponse });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    const element = render('H:12345678');
    const directive = element.find('grr-comparison-chart:nth(1)');
    const directiveTypedData =
        directive.scope().$eval(directive.attr('typed-data'));
    expect(directiveTypedData['value']).toEqual({
      data: [
        {value: {label: {value: '< 16.6s'}, x: {value: 10.55}}},
        {value: {label: {value: '< 32768.6s'}, x: {value: 5.55}}},
        // Max range value of the last bucket should be ignored and
        // the one of the one-before-the-last bucket should be used.
        {value: {label: {value: '> 32768.6s'}, x: {value: 9.55}}},
      ]
    });
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
                       },
                       {
                         type: 'StatsHistogramBin',
                         value: {
                           num: {
                             type: 'long',
                             value: 9,
                           },
                           range_max_value: {
                             type: 'float',
                             value: 62768.0,
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

       const deferred = $q.defer();
       deferred.resolve({data: statsResponse});
       spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

       const element = render('H:12345678');
       const directive = element.find('grr-comparison-chart:nth(2)');
       const directiveTypedData =
           directive.scope().$eval(directive.attr('typed-data'));
       expect(directiveTypedData['value']).toEqual({
         data: [
           {value: {label: {value: '< 16 B'}, x: {value: 10}}},
           {value: {label: {value: '< 32 KiB'}, x: {value: 5}}},
           // Max range value of the last bucket should be ignored and
           // the one of the one-before-the-last bucket should be used.
           {value: {label: {value: '> 32 KiB'}, x: {value: 9}}},
         ]
       });
     });
});


exports = {};
