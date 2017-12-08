'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('stat ext-flags for Linux directive', function() {
  let $compile, $rootScope;

  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));
  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  let render = function(value) {
    $rootScope.value = value;

    let template = '<grr-stat-ext-flags-linux value="value" />';
    let element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('handles empty values', function() {
    let element = render(undefined);
    expect(element.text().trim()).toBe('none');
  });

  it('handles incorrect input type', function() {
    let element = render({value: 'foo'});
    expect(element.text().trim()).toBe('malformed');
  });

  it('handles negative values', function() {
    let element = render({value: -1});
    expect(element.text().trim()).toBe('malformed');
  });

  it('handles non-integer values', function() {
    let element = render({value: 5.13});
    expect(element.text().trim()).toBe('malformed');
  });

  it('indicates files without special flags', function() {
    let element = render({value: 0});
    expect(element.text().trim()).toBe('--------------------');
  });

  it('indicates regular files', function() {
    let element = render({value: 524288});
    expect(element.text().trim()).toBe('-----------------e--');
  });

  it('indicates immutable files', function() {
    let element = render({value: 524304});
    expect(element.text().trim()).toBe('----i------------e--');
  });

  it('indicates files non-dumpable support', function() {
    let element = render({value: 524352});
    expect(element.text().trim()).toBe('------d----------e--');
  });
});
