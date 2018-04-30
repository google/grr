'use strict';

goog.module('grrUi.flow.flowResultsDirectiveTest');

const {flowModule} = goog.require('grrUi.flow.flow');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('flow results directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module('/static/angular-components/flow/flow-results.html'));
  beforeEach(module(flowModule.name));
  beforeEach(module(testsModule.name));

  // Stub out grrResultsCollection directive, as all rendering is going
  // to be delegated to it.
  stubDirective('grrResultsCollection');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (flowId) => {
    $rootScope.flowId = flowId;
    $rootScope.apiBasePath = 'foo/bar';

    const template = '<grr-flow-results flow-id="flowId" ' +
        'api-base-path="apiBasePath" />';

    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('delegates rendering to grr-results-collection directive', () => {
    const element = renderTestTemplate('F:1234');
    const directive = element.find('grr-results-collection:nth(0)');
    expect(directive.length).toBe(1);
  });

  it('builds grr-result-collection urls correctly', () => {
    const element = renderTestTemplate('F:1234');
    const directive = element.find('grr-results-collection:nth(0)');
    expect(directive.scope().$eval(directive.attr('results-url'))).toEqual(
        'foo/bar/F:1234/results');
    expect(
        directive.scope().$eval(directive.attr('output-plugins-url'))).toEqual(
            'foo/bar/F:1234/output-plugins');
    expect(
        directive.scope().$eval(directive.attr('download-files-url'))).toEqual(
            'foo/bar/F:1234/results/files-archive');
  });
});


exports = {};
