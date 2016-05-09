'use strict';

goog.require('grrUi.flow.module');
goog.require('grrUi.tests.module');

describe('start flow form directive', function() {
  var $compile, $rootScope, $q, grrApiService, grrReflectionService;

  beforeEach(module('/static/angular-components/flow/start-flow-form.html'));
  beforeEach(module(grrUi.flow.module.name));
  beforeEach(module(grrUi.tests.module.name));

  // Stub out grr-semantic-value, grr-form-value and
  // grr-form-proto-repeated-field directives, as all rendering is going to
  // be delegated to them.
  angular.forEach(
      ['grrFormValue',
       'grrFormProtoRepeatedField',
       'grrSemanticValue'],
      function(directiveName) {
        grrUi.tests.stubDirective(directiveName);
      });

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    grrReflectionService = $injector.get('grrReflectionService');

    spyOn(grrReflectionService, 'getRDFValueDescriptor').and.callFake(
        function(valueType) {
          var deferred = $q.defer();

          if (valueType == 'FlowRunnerArgs') {
            deferred.resolve({
              default: {
                type: 'FlowRunnerArgs',
                value: {
                  flow_name: 'FooFlow',
                  output_plugins: [
                    {
                      foo: 'bar'
                    }
                  ],
                  foo: 'bar'
                }
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

  var renderTestTemplate = function() {
    $rootScope.clientId = 'C.0000111122223333';
    $rootScope.descriptor = {
      type: 'ApiFlowDescriptor',
      value: {
        name: {
          type: 'RDFString',
          value: 'FooFlow'
        },
        default_args: {
          type: 'FooFlowArgs',
          value: {
            foo: 'bar'
          }
        }
      }
    };

    var template = '<grr-start-flow-form ' +
        'client-id="clientId" descriptor="descriptor" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows flow arguments form', function() {
    var element = renderTestTemplate();
    var directive = element.find('grr-form-value:nth(0)');

    expect(directive.scope().$eval(directive.attr('value'))).toEqual(
        $rootScope.descriptor['value']['default_args']);
  });

  it('shows flow runner arguments form', function() {
    var element = renderTestTemplate();
    var directive = element.find('grr-form-value:nth(1)');

    // This should be equal to flow runner arguments default.
    expect(directive.scope().$eval(directive.attr('value'))).toEqual({
      type: 'FlowRunnerArgs',
      value: {
        flow_name: {
          value: 'FooFlow',
          type: 'RDFString'
        },
        output_plugins: [],
        foo: 'bar'
      }
    });
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

  it('sends request when Launch button is clicked', function() {
    var element = renderTestTemplate();

    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    browserTrigger(element.find('button.Launch'), 'click');

    expect(grrApiService.post).toHaveBeenCalledWith(
        '/clients/C.0000111122223333/flows', {
          flow: {
            runner_args: {
              flow_name: 'FooFlow',
              output_plugins: [],
              foo: 'bar'
            },
            args: {
              foo: 'bar'
            }
          }
        });
  });

  it('respects changes in form data when sending request', function() {
    var element = renderTestTemplate();

    // Change flow args.
    var directive = element.find('grr-form-value:nth(0)');
    directive.scope().$eval(directive.attr('value'))['value']['changed'] = true;

    // Change flow runner args.
    directive = element.find('grr-form-value:nth(1)');
    directive.scope().$eval(directive.attr('value'))['value']['changed'] = true;

    // Change output plugins value.
    directive = element.find('grr-form-proto-repeated-field');
    directive.scope().$eval(directive.attr('value')).push(42);

    // Apply the changes.
    $rootScope.$apply();

    // Now click the Launch button.
    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);
    browserTrigger(element.find('button.Launch'), 'click');

    expect(grrApiService.post).toHaveBeenCalledWith(
        '/clients/C.0000111122223333/flows', {
          flow: {
            runner_args: {
              flow_name: 'FooFlow',
              output_plugins: [42],
              changed: true,
              foo: 'bar'
            },
            args: {
              foo: 'bar',
              changed: true
            }
          }
        });
  });

  it('shows progress message when request is processed', function() {
    var element = renderTestTemplate();

    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    browserTrigger(element.find('button.Launch'), 'click');

    expect(element.text()).toContain('Launching flow FooFlow...');
  });

  it('shows flow summary when launch succeeds', function() {
    var element = renderTestTemplate();

    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    browserTrigger(element.find('button.Launch'), 'click');

    var flow = {
      args: {'foo1': 'bar1'},
      runner_args: {'foo2': 'bar2'}
    };
    deferred.resolve({
      data: flow
    });
    $rootScope.$apply();

    var directive = element.find('grr-semantic-value:nth(0)');
    expect(directive.scope().$eval(directive.attr('value'))).toEqual(flow);
  });

  it('shows failure message when launch fails', function() {
    var element = renderTestTemplate();

    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    browserTrigger(element.find('button.Launch'), 'click');

    deferred.reject({
      data: {
        message: 'Something is wrong'
      }
    });
    $rootScope.$apply();

    expect(element.text()).toContain('Something is wrong');
  });

});
