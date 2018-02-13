'use strict';

goog.module('grrUi.outputPlugins.outputPluginsNotesDirectiveTest');

const {outputPluginsModule} = goog.require('grrUi.outputPlugins.outputPlugins');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('output plugins notes list directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;


  beforeEach(module('/static/angular-components/output-plugins/' +
        'output-plugins-notes.html'));
  beforeEach(module(outputPluginsModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrOutputPluginNote');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
  }));

  const renderTestTemplate = () => {
    $rootScope.outputPluginsUrl = '/foo/bar/plugins';

    const template = '<grr-output-plugins-notes ' +
        'output-plugins-url="outputPluginsUrl" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('requests output plugins metadata via API service', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    renderTestTemplate();

    expect(grrApiService.get).toHaveBeenCalledWith('/foo/bar/plugins');
  });

  it('shows an error when API request fails', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);
    deferred.reject({data: {message: 'FAIL'}});

    const element = renderTestTemplate();
    expect(element.text()).toContain('Can\'t fetch output plugins list: ' +
        'FAIL');
  });

  it('delegates every plugin display to grr-output-plugin-note', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    const plugin1 = {
      value: 'foo',
    };
    const plugin2 = {
      value: 'bar',
    };
    deferred.resolve({
      data: {
        items: [plugin1, plugin2],
      },
    });

    const element = renderTestTemplate();
    expect(element.find('grr-output-plugin-note').length).toBe(2);

    let directive = element.find('grr-output-plugin-note:nth(0)');
    expect(directive.scope().$eval(directive.attr('output-plugin'))).toEqual(
        plugin1);

    directive = element.find('grr-output-plugin-note:nth(1)');
    expect(directive.scope().$eval(directive.attr('output-plugin'))).toEqual(
        plugin2);
  });
});


exports = {};
