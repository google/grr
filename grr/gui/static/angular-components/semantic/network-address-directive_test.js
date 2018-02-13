'use strict';

goog.module('grrUi.semantic.networkAddressDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


describe('mac address directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-network-address value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows "-" when value is null', () => {
    const element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('-');
  });

  it('shows IPv4 value for IPv4 address without metadata', () => {
    const element = renderTestTemplate({
      packed_bytes: '+BZUBn',
      address_type: 'INET',
    });
    expect(element.text()).toContain('248.22.84.06');
  });

  it('shows IPv4 value for IPv4 address with metadata', () => {
    const element = renderTestTemplate({
      value: {
        packed_bytes: {value: '+BZUBn'},
        address_type: {value: 'INET'},
      },
    });
    expect(element.text()).toContain('248.22.84.06');
  });

  it('shows IPv6 value for IPv6 address without metadata', () => {
    const element = renderTestTemplate({
      packed_bytes: '+BZUBnliBnl',
      address_type: 'INET6',
    });
    expect(element.text()).toContain('f816:5406:7962:0679');
  });

  it('shows IPv6 value for IPv6 address with metadata', () => {
    const element = renderTestTemplate({
      value: {
        packed_bytes: {
          value: '+BZUBnliBnl',
        },
        address_type: {
          value: 'INET6',
        },
      },
    });
    expect(element.text()).toContain('f816:5406:7962:0679');
  });
});


exports = {};
