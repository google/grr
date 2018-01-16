'use strict';

goog.provide('grrUi.semantic.statExtFlagsOsxDirectiveTest');
goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

const HTML_TEMPLATE_URL =
    '/static/angular-components/semantic/stat-ext-flags-osx.html';

describe('stat ext-flags for Mac directive', function() {
  let $compile, $rootScope;

  beforeEach(module(HTML_TEMPLATE_URL));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));
  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const render = function(value) {
    $rootScope.value = value;

    const template = '<grr-stat-ext-flags-osx value="value" />';
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
    const element = render({vaue: -42});
    expect(element.text().trim()).toBe('malformed');
  });

  it('handles non-integer values', function() {
    const element = render({value: 3.14});
    expect(element.text().trim()).toBe('malformed');
  });

  it('indicates regular files', function() {
    const element = render({value: 0});
    expect(element.text().trim()).toBe('');
  });

  it('indicates immutable files', function() {
    const element = render({value: 2});
    expect(element.text().trim()).toBe('uchg');
  });

  it('indicates files with nodump flag', function() {
    const element = render({value: 1});
    expect(element.text().trim()).toBe('nodump');
  });

  it('indicates files with multiple flags', function() {
    const element = render({value: 196616});
    const text = element.text().trim();
    expect(text).toContain('opaque');
    expect(text).toContain('arch');
    expect(text).toContain('schg');
  });

  it('ignores flags with unknown keywords', function() {
    const element = render({value: 32});
    expect(element.text().trim()).toBe('');
  });
});
