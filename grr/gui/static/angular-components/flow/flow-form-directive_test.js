'use strict';

goog.require('grrUi.flow.module');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');

describe('flow form directive', function() {
  var $compile, $rootScope, $q, grrReflectionService;

  beforeEach(module('/static/angular-components/flow/flow-form.html'));
  beforeEach(module(grrUi.flow.module.name));
  beforeEach(module(grrUi.tests.module.name));

  // Stub out grr-form-value and grr-form-proto-repeated-field directives,
  // as all rendering is going to be delegated to them.
  angular.forEach(
      ['grrFormValue',
       'grrFormProtoRepeatedField'],
      function(directiveName) {
        grrUi.tests.stubDirective(directiveName);
      });

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    spyOn(grrReflectionService, 'getRDFValueDescriptor').and.callFake(
        function(valueType) {
          var deferred = $q.defer();

          if (valueType == 'FlowRunnerArgs') {
            deferred.resolve({
              default: {
                type: 'FlowRunnerArgs',
                value: {}
              },
              fields: [
                {
                  name: 'output_plugins',
                  default: [],
                  foo: 'bar'
                }
              ]
            });
          } else if (valueType == 'OutputPluginDescriptor') {
            deferred.resolve({
              default: {
                type: 'OutputPluginDescriptor',
                value: 'OutputPluginDescriptor-default',
                foo: 'bar'
              }
            });
          }

          return deferred.promise;
        });
  }));

  var renderTestTemplate = function(args, runnerArgs, withOutputPlugins) {
    $rootScope.clientId = 'C.0000111122223333';
    $rootScope.args = args || {
          type: 'FooFlowArgs',
          value: {
            foo: 'bar'
          }
    };

    $rootScope.runnerArgs = runnerArgs || {
      type: 'FlowRunnerArgs',
      value: {
        flow_name: {
          type: 'RDFString',
          value: 'FooFlow'
        }
      }
    };

    if (angular.isUndefined(withOutputPlugins)) {
      withOutputPlugins = true;
    }
    $rootScope.withOutputPlugins = withOutputPlugins;

    var template = '<grr-flow-form ' +
        'flow-args="args" flow-runner-args="runnerArgs" ' +
        'with-output-plugins="withOutputPlugins" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows flow arguments form', function() {
    var element = renderTestTemplate();
    var directive = element.find('grr-form-value:nth(0)');

    expect(directive.scope().$eval(directive.attr('value'))).toEqual(
        $rootScope.args);
  });

  it('shows flow runner arguments form', function() {
    var element = renderTestTemplate();
    var directive = element.find('grr-form-value:nth(1)');

    // This should be equal to flow runner arguments default + initialized
    // empty output plugins list.
    var expected = angular.copy($rootScope.runnerArgs);
    expected['value']['output_plugins'] = [];
    expect(directive.scope().$eval(directive.attr('value'))).toEqual(expected);
  });

  it('preserves existing output plugins list', function() {
    var runnerArgs = {
      type: 'FlowRunnerArgs',
      value: {
        flow_name: {
          type: 'RDFString',
          value: 'FooFlow'
        },
        output_plugins: [
          {
            type: 'FooPluginArgs',
            value: {}
          }
        ]
      }
    };
    var element = renderTestTemplate(undefined, angular.copy(runnerArgs));
    var directive = element.find('grr-form-value:nth(1)');
    expect(directive.scope().$eval(directive.attr('value'))).toEqual(runnerArgs);
  });

  it('does not show output plugins if with-output-plugns=false', function() {
    var element = renderTestTemplate(undefined, undefined, false);
    var directive = element.find('grr-form-value:nth(1)');

    // This should be equal to flow runner arguments default. output_plugins
    // list is not initialized as no output plugins form controls are present.
    expect(directive.scope().$eval(directive.attr('value'))).toEqual(
        angular.copy($rootScope.runnerArgs));

    var pluginsDirective = element.find('grr-form-proto-repeated-field');
    expect(pluginsDirective.length).toBe(0);
  });

  it('shows output plugins list form', function() {
    var element = renderTestTemplate();
    var directive = element.find('grr-form-proto-repeated-field');

    // This should be equal to output plugin descriptor.
    expect(directive.scope().$eval(directive.attr('descriptor'))).toEqual({
      default: {
        type: 'OutputPluginDescriptor',
        value: 'OutputPluginDescriptor-default',
        foo: 'bar'
      }
    });

    // This should be equal to output plugins field from flor runner arguments
    // descriptor.
    expect(directive.scope().$eval(directive.attr('field'))).toEqual({
      name: 'output_plugins',
      default: [],
      foo: 'bar'
    });

    // Output plugins list is empty by default.
    expect(directive.scope().$eval(directive.attr('value'))).toEqual([]);
  });

});
