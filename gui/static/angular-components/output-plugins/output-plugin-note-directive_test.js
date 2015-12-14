'use strict';

goog.require('grrUi.outputPlugins.module');
goog.require('grrUi.tests.module');


describe('output plugin note directive', function() {
  var $compile, $rootScope;
  var grrOutputPluginsDirectivesRegistryService;

  beforeEach(module('/static/angular-components/output-plugins/output-plugin-note.html'));
  beforeEach(module(grrUi.outputPlugins.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrOutputPluginNoteBody');
  grrUi.tests.stubDirective('grrOutputPluginLogs');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');

    grrOutputPluginsDirectivesRegistryService = $injector.get(
        'grrOutputPluginsDirectivesRegistryService');
  }));

  var defaultOutputPlugin = {
    value: {
      plugin_descriptor: {
        value: {
          plugin_name: {
            value: 'Foo'
          }
        }
      },
      id: {
        value: '42'
      }
    }
  };

  var renderTestTemplate = function(outputPlugin) {
    $rootScope.outputPlugin = outputPlugin || angular.copy(defaultOutputPlugin);
    $rootScope.outputPluginsUrl = '/foo/bar';

    var template = '<grr-output-plugin-note output-plugin="outputPlugin" ' +
        'output-plugins-url="outputPluginsUrl" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows registered plugin title if registered', function() {
    var element = renderTestTemplate();
    expect(element.text()).toContain('');

    var directiveMock = {
      directive_name: 'theTestDirective',
      output_plugin_title: 'a bar plugin'
    };
    grrOutputPluginsDirectivesRegistryService.registerDirective(
        'Foo', directiveMock);

    var element = renderTestTemplate();
    expect(element.text()).toContain('a bar plugin');
  });

  it('shows plugin descriptor name if not registered', function() {
    var element = renderTestTemplate();
    expect(element.text()).toContain('Foo');
  });

  it('delegates rendering to grr-output-plugin-note-body', function() {
    var element = renderTestTemplate();

    var body = element.find('grr-output-plugin-note-body');
    expect(body.scope().$eval(body.attr('output-plugin'))).toEqual(
        defaultOutputPlugin);
  });

  it('delegates logs info rendering to grr-output-plugin-logs', function() {
    var element = renderTestTemplate();

    var logs = element.find('grr-output-plugin-logs:nth(0)');
    expect(logs.scope().$eval(logs.attr('url'))).toEqual(
        '/foo/bar/42/logs');
  });

  it('delegates errors info rendering to grr-output-plugin-logs', function() {
    var element = renderTestTemplate();

    var errors = element.find('grr-output-plugin-logs:nth(1)');
    expect(errors.scope().$eval(errors.attr('url'))).toEqual(
        '/foo/bar/42/errors');
  });
});
