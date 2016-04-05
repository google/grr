'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('stat mode directive', function() {
  var $compile, $rootScope;

  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var render = function(value) {
    $rootScope.value = value;

    var template = '<grr-stat-mode value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does not show anything when value is null', function() {
    var element = render(null);
    expect(element.text().trim()).toBe('-');
  });

  it('does not show anything when value is empty', function() {
    var element = render({});
    expect(element.text().trim()).toBe('-');
  });

  it('indicates regular files', function() {
    var element = render({value: 33188});
    expect(element.text().trim()).toBe('-rw-r--r--');
  });

  it('indicates directories', function() {
    var element = render({value: 16832});
    expect(element.text().trim()).toBe('drwx------');
  });

  it('indicates character devices', function() {
    var element = render({value: 8592});
    expect(element.text().trim()).toBe('crw--w----');
  });

  it('indicates symbolic links', function() {
    var element = render({value: 41325});
    expect(element.text().trim()).toBe('lr-xr-xr-x');
  });

  it('indicates block devices', function() {
    var element = render({value: 24960});
    expect(element.text().trim()).toBe('brw-------');
  });

  it('indicates FIFO pipes', function() {
    var element = render({value: 4516});
    expect(element.text().trim()).toBe('prw-r--r--');
  });

  it('indicates sockets', function() {
    var element = render({value: 50668});
    expect(element.text().trim()).toBe('srwxr-sr--');
  });

  it('considers the S_ISUID flag', function() {
    var element = render({value: 35300});
    expect(element.text().trim()).toBe('-rwsr--r--');

    var element = render({value: 35236});
    expect(element.text().trim()).toBe('-rwSr--r--');
  });

  it('considers the S_ISGID flag', function() {
    var element = render({value: 36332});
    expect(element.text().trim()).toBe('-rwsr-sr--');

    var element = render({value: 36324});
    expect(element.text().trim()).toBe('-rwsr-Sr--');
  });

  it('considers the S_ISVTX flag', function() {
    var element = render({value: 35812});
    expect(element.text().trim()).toBe('-rwsr--r-T');

    element = render({value: 35813});
    expect(element.text().trim()).toBe('-rwsr--r-t');
  });

});
