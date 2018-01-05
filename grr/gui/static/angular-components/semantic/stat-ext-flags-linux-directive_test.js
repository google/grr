'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

const HTML_TEMPLATE_PATH =
    '/static/angular-components/semantic/stat-ext-flags-linux.html';

describe('stat ext-flags for Linux directive', function() {
  let $compile, $rootScope;

  beforeEach(module(HTML_TEMPLATE_PATH));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));
  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const render = function(value) {
    $rootScope.value = value;

    const template = '<grr-stat-ext-flags-linux value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('handles empty values', function() {
    const element = render(undefined);
    expect(element.text().trim()).toBe('none');
  });

  it('handles incorrect input type', function() {
    const element = render({value: 'foo'});
    expect(element.text().trim()).toBe('malformed');
  });

  it('handles negative values', function() {
    const element = render({value: -1});
    expect(element.text().trim()).toBe('malformed');
  });

  it('handles non-integer values', function() {
    const element = render({value: 5.13});
    expect(element.text().trim()).toBe('malformed');
  });

  it('indicates files without special flags', function() {
    const element = render({value: 0});
    expect(element.text().replace(/\s/g, '')).toBe('--------------------');
  });

  it('indicates regular files', function() {
    const element = render({value: 524288});
    expect(element.text().replace(/\s/g, '')).toBe('-----------------e--');
  });

  it('indicates immutable files', function() {
    const element = render({value: 524304});
    expect(element.text().replace(/\s/g, '')).toBe('----i------------e--');
  });

  it('indicates files non-dumpable support', function() {
    const element = render({value: 524352});
    expect(element.text().replace(/\s/g, '')).toBe('------d----------e--');
  });
});
