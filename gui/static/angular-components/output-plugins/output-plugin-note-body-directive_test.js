'use strict';

goog.require('grrUi.outputPlugins.module');
goog.require('grrUi.tests.module');


describe('output plugin note directive', function() {
  var $compile, $rootScope;
  var grrOutputPluginsDirectivesRegistryService;

  beforeEach(module(grrUi.outputPlugins.module.name));
  beforeEach(module(grrUi.tests.module.name));

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
      }
    }
  };

  var renderTestTemplate = function(outputPlugin) {
    $rootScope.outputPlugin = outputPlugin || angular.copy(defaultOutputPlugin);

    var template = '<grr-output-plugin-note-body ' +
        'output-plugin="outputPlugin" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing if no corresponding directive found', function() {
    var element = renderTestTemplate();
    expect(element.text().trim()).toBe('');
  });

  it('renders registered type with a corresponding directive', function() {
    // This directive does not exist and Angular won't process it,
    // but it still will be inserted into DOM and we can check
    // that it's inserted correctly.
    var directiveMock = {
      directive_name: 'theTestDirective'
    };

    grrOutputPluginsDirectivesRegistryService.registerDirective(
        'Foo', directiveMock);

    var element = renderTestTemplate();
    expect($('the-test-directive', element).length).toBe(1);
  });

  it('passes outputPlugin to the corresponding directive', function() {
    var directiveMock = {
      directive_name: 'theTestDirective'
    };

    grrOutputPluginsDirectivesRegistryService.registerDirective(
        'Foo', directiveMock);

    var element = renderTestTemplate();
    var directive = element.find('the-test-directive');
    expect(directive.scope().$eval(directive.attr('output-plugin'))).toEqual(
        defaultOutputPlugin);
  });

});
