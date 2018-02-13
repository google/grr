'use strict';

goog.module('grrUi.semantic.statExtFlagsLinuxDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


const HTML_TEMPLATE_PATH =
    '/static/angular-components/semantic/stat-ext-flags-linux.html';

describe('stat ext-flags for Linux directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module(HTML_TEMPLATE_PATH));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));
  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const render = (value) => {
    $rootScope.value = value;

    const template = '<grr-stat-ext-flags-linux value="value" />';
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
    const element = render({value: -1});
    expect(element.text().trim()).toBe('malformed');
  });

  it('handles non-integer values', () => {
    const element = render({value: 5.13});
    expect(element.text().trim()).toBe('malformed');
  });

  it('indicates files without special flags', () => {
    const element = render({value: 0});
    expect(element.text().replace(/\s/g, '')).toBe('--------------------');
  });

  it('indicates regular files', () => {
    const element = render({value: 524288});
    expect(element.text().replace(/\s/g, '')).toBe('-----------------e--');
  });

  it('indicates immutable files', () => {
    const element = render({value: 524304});
    expect(element.text().replace(/\s/g, '')).toBe('----i------------e--');
  });

  it('indicates files non-dumpable support', () => {
    const element = render({value: 524352});
    expect(element.text().replace(/\s/g, '')).toBe('------d----------e--');
  });
});


exports = {};
