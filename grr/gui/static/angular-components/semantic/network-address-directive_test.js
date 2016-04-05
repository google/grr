'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('mac address directive', function() {
  var $compile, $rootScope;

  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-network-address value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows "-" when value is null', function() {
    var element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('-');
  });

  it('shows IPv4 value for IPv4 address without metadata', function() {
    var element = renderTestTemplate({
      packed_bytes: '+BZUBn',
      address_type: 'INET'
    });
    expect(element.text()).toContain('248.22.84.06');
  });

  it('shows IPv4 value for IPv4 address with metadata', function() {
    var element = renderTestTemplate({
      value: {
        packed_bytes: {value: '+BZUBn'},
        address_type: {value: 'INET'}
      }
    });
    expect(element.text()).toContain('248.22.84.06');
  });

  it('shows IPv6 value for IPv6 address without metadata', function() {
    var element = renderTestTemplate({
      packed_bytes: '+BZUBnliBnl',
      address_type: 'INET6'
    });
    expect(element.text()).toContain('f816:5406:7962:0679');
  });

  it('shows IPv6 value for IPv6 address with metadata', function() {
    var element = renderTestTemplate({
      value: {
        packed_bytes: {
          value: '+BZUBnliBnl'
        },
        address_type: {
          value: 'INET6'
        }
      }
    });
    expect(element.text()).toContain('f816:5406:7962:0679');
  });

});
