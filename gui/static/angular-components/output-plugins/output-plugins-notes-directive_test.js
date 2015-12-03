'use strict';

goog.require('grrUi.outputPlugins.module');
goog.require('grrUi.tests.module');


describe('output plugins notes list directive', function() {
  var $compile, $rootScope, $q, grrApiService;

  beforeEach(module('/static/angular-components/output-plugins/' +
        'output-plugins-notes.html'));
  beforeEach(module(grrUi.outputPlugins.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrOutputPluginNote');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
  }));

  var renderTestTemplate = function() {
    $rootScope.outputPluginsUrl = '/foo/bar/plugins';

    var template = '<grr-output-plugins-notes ' +
        'output-plugins-url="outputPluginsUrl" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('requests output plugins metadata via API service', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    var element = renderTestTemplate();

    expect(grrApiService.get).toHaveBeenCalledWith('/foo/bar/plugins');
  });

  it('shows an error when API request fails', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);
    deferred.reject({data: {message: 'FAIL'}});

    var element = renderTestTemplate();
    expect(element.text()).toContain('Can\'t fetch output plugins list: ' +
        'FAIL');
  });

  it('delegates every plugin display to grr-output-plugin-note', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    var plugin1 = {
      value: 'foo'
    };
    var plugin2 = {
      value: 'bar'
    };
    deferred.resolve({
      data: {
        items: [plugin1, plugin2]
      }
    });

    var element = renderTestTemplate();
    expect(element.find('grr-output-plugin-note').length).toBe(2);

    var directive = element.find('grr-output-plugin-note:nth(0)');
    expect(directive.scope().$eval(directive.attr('output-plugin'))).toEqual(
        plugin1);

    directive = element.find('grr-output-plugin-note:nth(1)');
    expect(directive.scope().$eval(directive.attr('output-plugin'))).toEqual(
        plugin2);
  });
});
