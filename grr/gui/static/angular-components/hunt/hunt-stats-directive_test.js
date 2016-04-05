'use strict';

goog.require('grrUi.hunt.module');
goog.require('grrUi.tests.module');

describe('hunt stats directive', function() {
  var $compile, $rootScope, $q, grrApiService;

  beforeEach(module('/static/angular-components/hunt/hunt-stats.html'));
  beforeEach(module(grrUi.hunt.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');

  }));

  var render = function(huntUrn) {
    $rootScope.huntUrn = huntUrn;

    var template = '<grr-hunt-stats hunt-urn="huntUrn" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows user cpu usage histogram', function() {
    var statsResponse = {
      stats: {
        type: "ClientResourcesStats",
        value: {
          user_cpu_stats: {
            type: "RunningStats",
            value: {
              histogram: {
                type: "StatsHistogram",
                value: {
                  bins: [{
                    type: "StatsHistogramBin",
                    value: {
                      num: {
                        type: "long",
                        value: 10.55
                      },
                      range_max_value: {
                        type: "float",
                        value: 16.55
                      }
                    }
                  }, {
                    type: "StatsHistogramBin",
                    value: {
                      num: {
                        type: "long",
                        value: 5.55
                      },
                      range_max_value: {
                        type: "float",
                        value: 32768.55
                      }
                    }
                  }]
                }
              }
            }
          }
        }
      }
    };

    // Mock $.plot.
    $.plot = jasmine.createSpy("$.plot spy").and.callFake(function(element, series, options){
      expect(element.hasClass('user-cpu-histogram')).toBeTruthy();
      expect(series[0].data.length).toEqual(2);
      expect(series[0].data[0]).toEqual([0, 10.55]);
      expect(series[0].data[1]).toEqual([1, 5.55]);
      expect(options.xaxis.ticks).toEqual([[0.5, '16.6'], [1.5, '32768.6']]);
    });

    var deferred = $q.defer();
    deferred.resolve({ data: statsResponse });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    var element = render('H:12345678');
    expect(grrApiService.get).toHaveBeenCalledWith('/hunts/H:12345678/stats');
    expect($.plot).toHaveBeenCalled();
  });

  it('shows system cpu usage histogram', function() {
    var statsResponse = {
      stats: {
        type: "ClientResourcesStats",
        value: {
          system_cpu_stats: {
            type: "RunningStats",
            value: {
              histogram: {
                type: "StatsHistogram",
                value: {
                  bins: [{
                    type: "StatsHistogramBin",
                    value: {
                      num: {
                        type: "long",
                        value: 10.55
                      },
                      range_max_value: {
                        type: "float",
                        value: 16.55
                      }
                    }
                  }, {
                    type: "StatsHistogramBin",
                    value: {
                      num: {
                        type: "long",
                        value: 5.55
                      },
                      range_max_value: {
                        type: "float",
                        value: 32768.55
                      }
                    }
                  }]
                }
              }
            }
          }
        }
      }
    };

    // Mock $.plot.
    $.plot = jasmine.createSpy("$.plot spy").and.callFake(function(element, series, options){
      expect(element.hasClass('system-cpu-histogram')).toBeTruthy();
      expect(series[0].data.length).toEqual(2);
      expect(series[0].data[0]).toEqual([0, 10.55]);
      expect(series[0].data[1]).toEqual([1, 5.55]);
      expect(options.xaxis.ticks).toEqual([[0.5, '16.6'], [1.5, '32768.6']]);
    });

    var deferred = $q.defer();
    deferred.resolve({ data: statsResponse });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    var element = render('H:12345678');
    expect(grrApiService.get).toHaveBeenCalledWith('/hunts/H:12345678/stats');
    expect($.plot).toHaveBeenCalled();
  });

  it('shows network bytes histogram with correct values and xaxis labels', function() {
    var statsResponse = {
      stats: {
        type: "ClientResourcesStats",
        value: {
          network_bytes_sent_stats: {
            type: "RunningStats",
            value: {
              histogram: {
                type: "StatsHistogram",
                value: {
                  bins: [{
                    type: "StatsHistogramBin",
                    value: {
                      num: {
                        type: "long",
                        value: 10
                      },
                      range_max_value: {
                        type: "float",
                        value: 16.0
                      }
                    }
                  }, {
                    type: "StatsHistogramBin",
                    value: {
                      num: {
                        type: "long",
                        value: 5
                      },
                      range_max_value: {
                        type: "float",
                        value: 32768.0
                      }
                    }
                  }]
                }
              }
            }
          }
        }
      }
    };

    // Mock $.plot.
    $.plot = jasmine.createSpy("$.plot spy").and.callFake(function(element, series, options){
      expect(element.hasClass('network-bytes-histogram')).toBeTruthy();
      expect(series[0].data.length).toEqual(2);
      expect(series[0].data[0]).toEqual([0, 10]);
      expect(series[0].data[1]).toEqual([1, 5]);
      expect(options.xaxis.ticks).toEqual([[0.5, '16B'], [1.5, '32K']]);
    });

    var deferred = $q.defer();
    deferred.resolve({ data: statsResponse });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    var element = render('H:12345678');
    expect(grrApiService.get).toHaveBeenCalledWith('/hunts/H:12345678/stats');
    expect($.plot).toHaveBeenCalled();
  });

});
