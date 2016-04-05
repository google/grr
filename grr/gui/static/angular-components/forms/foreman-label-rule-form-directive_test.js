'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.module');

describe('grr-form-label ForemanLabelClientRule selector ' +
         'directive', function() {
  var $compile, $rootScope, $q, grrReflectionService, grrApiService;

  beforeEach(module('/static/angular-components/forms/' +
                    'foreman-label-rule-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  // Stub out grr-form-value directive, as match mode selection rendering
  // is delegated to it.
  grrUi.tests.stubDirective('grrFormValue');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');
    grrApiService = $injector.get('grrApiService');

    spyOn(grrReflectionService, 'getRDFValueDescriptor').and.callFake(
        function(name) {
          var deferred = $q.defer();

          if (name == 'ForemanLabelClientRule') {
            deferred.resolve({
              default: {
                type: 'ForemanLabelClientRule',
                value: {}
              },
              fields: [{
                name: 'match_mode',
                default: {type: 'EnumNamedValue', value: 'MATCH_ALL'}
              }]
            });
          } else {
            throw new Error('Unexpected name: ' + name);
          }

          return deferred.promise;
        });

    spyOn(grrApiService, 'get').and.callFake(function(url) {
      if (url == '/clients/labels') {
        var deferred = $q.defer();

        deferred.resolve({
          data: {
            items: [
              {
                type: 'AFF4ObjectLabel',
                value: {
                  name: {
                    type: 'RDFString',
                    value: 'label_1'
                  }
                }
              },
              {
                type: 'AFF4ObjectLabel',
                value: {
                  name: {
                    type: 'RDFString',
                    value: 'label_2'
                  }
                }
              }
            ]
          }
        });

        return deferred.promise;
      } else {
        throw new Error('Unexpected url: ' + url);
      }
    });
  }));

  var renderTestTemplate = function(value) {
    if (angular.isUndefined(value)) {
      value = {
        type: 'ForemanLabelClientRule',
        value: {}
      };
    }

    $rootScope.value = value;

    var template = '<grr-form-label value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows list of labels', function() {
    var element = renderTestTemplate();

    expect(element.find('select option').length).toBe(2);
    expect(element.find('select option:nth(0)').attr('label')).toBe('label_1');
    expect(element.find('select option:nth(1)').attr('label')).toBe('label_2');
  });

  it('recognizes client label matching rule on init',
     function() {
    var value = {
      type: 'ForemanLabelClientRule',
      value: {
        label_names: [{
          type: 'unicode',
          value: 'label_2'
        }]
      }
    };

    var element = renderTestTemplate(value);

    expect(element.find('select').val()).toBe('string:label_2');
  });

});
