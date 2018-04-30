'use strict';

goog.module('grrUi.core.markdownDirectiveTest');

const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('markdown directive', () => {
  let $compile;
  let $rootScope;

  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (source) => {
    $rootScope.source = source;

    const template = '<grr-markdown source="source"></grr-markdown>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('renders markdown text', () => {
    const element = renderTestTemplate('*blah*');
    expect(element.html().trim()).toBe('<p><em>blah</em></p>');
  });
});


exports = {};
