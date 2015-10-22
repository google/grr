'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.module');

describe('grr-output-plugin-descriptor-form directive', function() {
  var $compile, $rootScope, $q, grrApiService, grrReflectionService;

  beforeEach(module('/static/angular-components/forms/' +
      'output-plugin-descriptor-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  // Stub out grr-form-value directive, as arguments rendering is going
  // to be delegated to it.
  grrUi.tests.stubDirective('grrFormValue');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    grrReflectionService = $injector.get('grrReflectionService');

    var apiServiceResponse = $q.defer();
    apiServiceResponse.resolve({
      data: {
        'FooOutputPlugin' : {
          args_type: 'FooOutputPluginArgs',
          name: 'FooOutputPlugin'
        },
        'BarOutputPlugin': {
          args_type: 'BarOutputPluginArgs',
          name: 'BarOutputPlugin'
        }
      }
    });
    spyOn(grrApiService, 'get').and.returnValue(apiServiceResponse.promise);

    spyOn(grrReflectionService, 'getRDFValueDescriptor').and
        .callFake(function(name) {
          var deferred = $q.defer();

          if (name == 'FooOutputPluginArgs') {
            deferred.resolve({
              default: {
                type: 'FooOutputPluginArgs',
                value: 'FooValue'
              }
            });
          } else if (name == 'BarOutputPluginArgs') {
            deferred.resolve({
              default: {
                type: 'BarOutputPluginArgs',
                value: 'BarValue'
              }
            });
          } else {
            throw new Error('Unexpected name: ' + name);
          }

          return deferred.promise;
        });
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = angular.isDefined(value) ? value : {
      type: 'OutputPluginDescriptor',
      value: {}
    };

    var template = '<grr-output-plugin-descriptor-form value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('selects alphabetically first plugin if none is specified', function() {
    var element = renderTestTemplate();

    expect($rootScope.value.value.plugin_name.value).toBe('BarOutputPlugin');
    expect(element.find('select').val()).toBe('string:BarOutputPlugin');
  });

  it('keeps current output plugin type if one is specified', function() {
    var element = renderTestTemplate({
      type: 'OutputPluginDescriptor',
      value: {
        plugin_name: {
          type: 'RDFString',
          value: 'FooOutputPlugin'
        }
      }
    });

    expect($rootScope.value.value.plugin_name.value).toBe('FooOutputPlugin');
    expect(element.find('select').val()).toBe('string:FooOutputPlugin');
  });

  it('sets plugin args to default when plugin type is changed', function() {
    var element = renderTestTemplate();

    expect($rootScope.value.value.plugin_args.type).toBe('BarOutputPluginArgs');

    element.find('select').val(
        element.find('select option[label="FooOutputPlugin"]').val());
    browserTrigger(element.find('select'), 'change');
    expect($rootScope.value.value.plugin_args.type).toBe('FooOutputPluginArgs');
  });

  it('delegates current plugin args rendering to grr-form-value', function() {
    var element = renderTestTemplate();

    var argsValue = $rootScope.$eval(
        element.find('grr-form-value').attr('value'));
    expect(argsValue.type).toBe('BarOutputPluginArgs');

    element.find('select').val(
        element.find('select option[label="FooOutputPlugin"]').val());
    browserTrigger(element.find('select'), 'change');

    argsValue = $rootScope.$eval(element.find('grr-form-value').attr('value'));
    expect(argsValue.type).toBe('FooOutputPluginArgs');
  });
});
