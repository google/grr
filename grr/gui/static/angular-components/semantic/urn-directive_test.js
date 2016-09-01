'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('urn directive', function() {
  var $compile, $rootScope, grrRoutingService;

  beforeEach(module('/static/angular-components/semantic/urn.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrRoutingService = $injector.get('grrRoutingService');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-urn value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does not show anything when value is empty', function() {
    var element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('');
  });

  it('shows plain string if grrRoutingService can\'t convert URN', function() {
    spyOn(grrUi.routing, 'aff4UrnToUrl').and.returnValue(undefined);

    var element = renderTestTemplate('aff4:/foo/bar');
    expect(element.text().trim()).toBe('aff4:/foo/bar');
    expect(element.find('a').length).toBe(0);
  });

  it('shows a link if grrRoutingService can convert URN', function() {
    spyOn(grrUi.routing, 'aff4UrnToUrl').and.returnValue({
      state: 'someState',
      params: {}
    });
    spyOn(grrRoutingService, 'href').and.returnValue('/some/real/link');

    var element = renderTestTemplate('aff4:/C.0001000200030004/fs/os/foo/bar');
    expect(element.find('a').text().trim()).toBe(
        'aff4:/C.0001000200030004/fs/os/foo/bar');
    expect(element.find('a').attr('href')).toBe(
        '/some/real/link');
  });
});
