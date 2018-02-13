'use strict';

goog.module('grrUi.client.clientStatusIconsDirectiveTest');

const {clientModule} = goog.require('grrUi.client.client');
const {testsModule} = goog.require('grrUi.tests');


describe('client status icons', () => {
  let $compile;
  let $rootScope;
  let grrTimeService;


  beforeEach(module('/static/angular-components/client/client-status-icons.html'));
  beforeEach(module(clientModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrTimeService = $injector.get('grrTimeService');
  }));

  const render = (client) => {
    $rootScope.client = client;

    const template = '<grr-client-status-icons client="client" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows online icon when last ping is 1 minute ago', () => {
    const client = {
      type: 'ApiClient',
      value: {
        'last_seen_at': {
          value: 42 * 1000000,
        },
      },
    };
    grrTimeService.getCurrentTimeMs = (() => (42 + 60) * 1000);

    const element = render(client);
    const iconElement = $('img[name=clientStatusIcon]', element);

    expect(iconElement.length).toBe(1);
    expect(iconElement[0].src).toContain('online.png');
    expect(iconElement[0].title).toBe('1 minutes ago');
  });

  it('shows online-1day icon when last ping is 23 hours ago', () => {
    const client = {
      type: 'ApiClient',
      value: {
        'last_seen_at': {
          value: 42 * 1000000,
        },
      },
    };
    grrTimeService.getCurrentTimeMs = (() => (42 + 60 * 60 * 23) * 1000);

    const element = render(client);
    const iconElement = $('img[name=clientStatusIcon]', element);

    expect(iconElement.length).toBe(1);
    expect(iconElement[0].src).toContain('online-1d.png');
    expect(iconElement[0].title).toBe('23 hours ago');
  });

  it('shows offline icon when last ping is is 3 days ago', () => {
    const client = {
      type: 'ApiClient',
      value: {
        'last_seen_at': {
          value: 42 * 1000000,
        },
      },
    };
    grrTimeService.getCurrentTimeMs = (() => (42 + 60 * 60 * 24 * 3) * 1000);

    const element = render(client);
    const iconElement = $('img[name=clientStatusIcon]', element);

    expect(iconElement.length).toBe(1);
    expect(iconElement[0].src).toContain('offline.png');
    expect(iconElement[0].title).toBe('3 days ago');
  });

  it('does not show crash icon if no crash happened', () => {
    const client = {
      type: 'ApiClient',
      value: {},
    };

    const element = render(client);
    const iconElement = $('img[name=clientCrashIcon]', element);

    expect(iconElement.length).toBe(0);
  });

  it('does not show crash icon if crash happened 1 week ago', () => {
    const client = {
      type: 'ApiClient',
      value: {
        'last_crash_at': {
          value: 42 * 1000000,
        },
      },
    };
    grrTimeService.getCurrentTimeMs = (() => (42 + 60 * 60 * 24 * 7) * 1000);

    const element = render(client);
    const iconElement = $('img[name=clientCrashIcon]', element);
    expect(iconElement.length).toBe(0);
  });

  it('shows crash icon if crash happened 1 hour ago', () => {
    const client = {
      type: 'ApiClient',
      value: {
        'last_crash_at': {
          value: 42 * 1000000,
        },
      },
    };
    grrTimeService.getCurrentTimeMs = (() => (42 + 60 * 60) * 1000);

    const element = render(client);
    const iconElement = $('img[name=clientCrashIcon]', element);

    expect(iconElement.length).toBe(1);
    expect(iconElement[0].src).toContain('skull-icon.png');
    expect(iconElement[0].title).toBe('1 hours ago');
  });

  it('shows no disk warning if none are present', () => {
    const element = render({
      type: 'ApiClient',
      value: {},
    });
    const warningElement = $('span[name=clientDiskWarnings]', element);
    expect(warningElement.length).toBe(0);
  });

  it('shows two disk warnings correctly', () => {
    const volume1 = {
      name: {
        value: '/Volume/A',
      },
      total_allocation_units: {
        value: 100,
      },
      actual_available_allocation_units: {
        value: 3,
      },
    };
    const volume2 = {
      name: {
        value: 'C:',
      },
      total_allocation_units: {
        value: 100,
      },
      actual_available_allocation_units: {
        value: 4,
      },
    };
    const client = {
      type: 'ApiClient',
      value: {
        volumes: [
          {
            type: 'Volume',
            value: volume1,
          },
          {
            type: 'Volume',
            value: volume2,
          },
        ],
      },
    };

    const element = render(client);
    const warningElement = $('span[name=clientDiskWarnings]', element);

    expect(warningElement.length).toBe(1);
    expect(warningElement.text()).toContain('/Volume/A 3% free');
    expect(warningElement.text()).toContain('C: 4% free');
  });
});


exports = {};
