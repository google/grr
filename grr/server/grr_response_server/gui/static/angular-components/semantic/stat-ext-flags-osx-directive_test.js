'use strict';

goog.module('grrUi.semantic.statExtFlagsOsxDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


const HTML_TEMPLATE_URL =
    '/static/angular-components/semantic/stat-ext-flags-osx.html';

describe('stat ext-flags for Mac directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module(HTML_TEMPLATE_URL));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));
  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const render = (value) => {
    $rootScope.value = value;

    const template = '<grr-stat-ext-flags-osx value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('handles empty values', () => {
    const element = render(undefined);
    expect(element.text().trim()).toBe('none');
  });

  it('handles incorrect input type', () => {
    const element = render({value: 'foo'});
    expect(element.text().trim()).toBe('malformed');
  });

  it('handles negative values', () => {
    const element = render({vaue: -42});
    expect(element.text().trim()).toBe('malformed');
  });

  it('handles non-integer values', () => {
    const element = render({value: 3.14});
    expect(element.text().trim()).toBe('malformed');
  });

  it('indicates regular files', () => {
    const element = render({value: 0});
    expect(element.text().trim()).toBe('');
  });

  it('indicates immutable files', () => {
    const element = render({value: 2});
    expect(element.text().trim()).toBe('uimmutable');
  });

  it('indicates files with nodump flag', () => {
    const element = render({value: 1});
    expect(element.text().trim()).toBe('nodump');
  });

  it('indicates files with multiple flags', () => {
    const element = render({value: 196616});
    const text = element.text().trim();
    expect(text).toContain('opaque');
    expect(text).toContain('archived');
    expect(text).toContain('simmutable');
  });

  it('ignores flags with unknown keywords', () => {
    const element = render({value: 32});
    expect(element.text().trim()).toBe('');
  });
});


exports = {};
