'use strict';

goog.require('grrUi.client.module');
goog.require('grrUi.tests.module');

describe('client status icons', function() {
  var $compile, $rootScope, grrTimeService;

  beforeEach(module('/static/angular-components/client/client-status-icons.html'));
  beforeEach(module(grrUi.client.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrTimeService = $injector.get('grrTimeService');
  }));

  var render = function(client) {
    $rootScope.client = client;

    var template = '<grr-client-status-icons client="client" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows online icon when last ping is 1 minute ago', function() {
    var client = {
      attributes: {
        'metadata:ping': {
          value: 42 * 1000000
        }
      }
    };
    grrTimeService.getCurrentTimeMs = function() {
      return (42 + 60) * 1000;
    };

    var element = render(client);
    var iconElement = $('img[name=clientStatusIcon]', element);

    expect(iconElement.length).toBe(1);
    expect(iconElement[0].src).toContain('online.png');
    expect(iconElement[0].title).toBe('1 minutes ago');
  });

  it('shows online-1day icon when last ping is 23 hours ago', function() {
    var client = {
      attributes: {
        'metadata:ping': {
          value: 42 * 1000000
        }
      }
    };
    grrTimeService.getCurrentTimeMs = function() {
      return (42 + 60 * 60 * 23) * 1000;
    };

    var element = render(client);
    var iconElement = $('img[name=clientStatusIcon]', element);

    expect(iconElement.length).toBe(1);
    expect(iconElement[0].src).toContain('online-1d.png');
    expect(iconElement[0].title).toBe('23 hours ago');
  });

  it('shows offline icon when last ping is is 3 days ago', function() {
    var client = {
      attributes: {
        'metadata:ping': {
          value: 42 * 1000000
        }
      }
    };
    grrTimeService.getCurrentTimeMs = function() {
      return (42 + 60 * 60 * 24 * 3) * 1000;
    };

    var element = render(client);
    var iconElement = $('img[name=clientStatusIcon]', element);

    expect(iconElement.length).toBe(1);
    expect(iconElement[0].src).toContain('offline.png');
    expect(iconElement[0].title).toBe('3 days ago');
  });

  it('does not show crash icon if no crash happened', function() {
    var client = {
      attributes: {
      }
    };

    var element = render(client);
    var iconElement = $('img[name=clientCrashIcon]', element);

    expect(iconElement.length).toBe(0);
  });

  it('does not show crash icon if crash happened 1 week ago', function() {
    var client = {
      attributes: {
        'aff4:last_crash': {
          value: {
            timestamp: {
              value: 42 * 1000000
            }
          }
        }
      }
    };
    grrTimeService.getCurrentTimeMs = function() {
      return (42 + 60 * 60 * 24 * 7) * 1000;
    };

    var element = render(client);
    var iconElement = $('img[name=clientCrashIcon]', element);
    expect(iconElement.length).toBe(0);
  });

  it('shows crash icon if crash happened 1 hour ago', function() {
    var client = {
      attributes: {
        'aff4:last_crash': {
          value: {
            timestamp: {
              value: 42 * 1000000
            }
          }
        }
      }
    };
    grrTimeService.getCurrentTimeMs = function() {
      return (42 + 60 * 60) * 1000;
    };

    var element = render(client);
    var iconElement = $('img[name=clientCrashIcon]', element);

    expect(iconElement.length).toBe(1);
    expect(iconElement[0].src).toContain('skull-icon.png');
    expect(iconElement[0].title).toBe('1 hours ago');
  });

  it('shows no disk warning if none are present', function() {
    var element = render({});
    var warningElement = $('span[name=clientDiskWarnings]', element);
    expect(warningElement.length).toBe(0);
  });

  it('shows two disk warnings correctly', function() {
    var client = {
      disk_warnings: [
        ['/Volume/A', 3],
        ['C:', 4]
      ]
    };
    var element = render(client);
    var warningElement = $('span[name=clientDiskWarnings]', element);

    expect(warningElement.length).toBe(1);
    expect(warningElement.text()).toContain('/Volume/A 3% free');
    expect(warningElement.text()).toContain('C: 4% free');
  });

});
