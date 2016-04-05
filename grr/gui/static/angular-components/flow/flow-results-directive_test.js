'use strict';

goog.require('grrUi.flow.module');
goog.require('grrUi.tests.module');

describe('flow results directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/flow/flow-results.html'));
  beforeEach(module(grrUi.flow.module.name));
  beforeEach(module(grrUi.tests.module.name));

  // Stub out grrResultsCollection directive, as all rendering is going
  // to be delegated to it.
  grrUi.tests.stubDirective('grrResultsCollection');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(flowUrn) {
    $rootScope.flowUrn = flowUrn;

    var template = '<grr-flow-results flow-urn="flowUrn" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('delegates rendering to grr-results-collection directive', function() {
    var element = renderTestTemplate('aff4:/C.0000111122223333/flows/F:1234');
    var directive = element.find('grr-results-collection:nth(0)');
    expect(directive.length).toBe(1);
  });

  it('handles flow urn starting with aff4', function() {
    var element = renderTestTemplate('aff4:/C.0000111122223333/flows/F:1234');
    var directive = element.find('grr-results-collection:nth(0)');
    expect(directive.scope().$eval(directive.attr('results-url'))).toEqual(
        '/clients/C.0000111122223333/flows/F:1234/results');
    expect(
        directive.scope().$eval(directive.attr('output-plugins-url'))).toEqual(
            '/clients/C.0000111122223333/flows/F:1234/output-plugins');
    expect(
        directive.scope().$eval(directive.attr('download-files-url'))).toEqual(
            '/clients/C.0000111122223333/flows/F:1234/results/files-archive');
  });

  it('handles flow urn not starting with aff4', function() {
    var element = renderTestTemplate('C.0000111122223333/flows/F:1234');
    var directive = element.find('grr-results-collection:nth(0)');
    expect(directive.scope().$eval(directive.attr('results-url'))).toEqual(
        '/clients/C.0000111122223333/flows/F:1234/results');
    expect(
        directive.scope().$eval(directive.attr('output-plugins-url'))).toEqual(
            '/clients/C.0000111122223333/flows/F:1234/output-plugins');
    expect(
        directive.scope().$eval(directive.attr('download-files-url'))).toEqual(
            '/clients/C.0000111122223333/flows/F:1234/results/files-archive');
  });

});
