'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');

describe('data object semantic directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/semantic/data-object.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrSemanticValue');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-data-object value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows empty table when value is empty', function() {
    var element = renderTestTemplate({
      type: 'ApiDataObject',
      value: {
      }
    });
    expect(element.find('table').length).toBe(1);
    expect(element.find('tr').length).toBe(0);
  });

  it('shows 2 rows for a data object with two key-value pairs', function() {
    var element = renderTestTemplate({
      type: 'ApiDataObject',
      value: {
        items: [{
          type: 'ApiDataObjectKeyValuePair',
          value: {
            key: {
              type: 'unicode',
              value: 'Test Integer Value'
            },
            value: {
              type: 'RDFInteger',
              value: 1000
            }
          }
        }, {
          type: 'ApiDataObjectKeyValuePair',
          value: {
            key: {
              type: 'unicode',
              value: 'Test String Value'
            },
            value: {
              type: 'RDFString',
              value: '<some value>'
            }
          }
        }]
      }
    });
    expect(element.find('table').length).toBe(1);
    expect(element.find('tr').length).toBe(2);

    expect(element.text()).toContain('Test Integer Value');
    expect(element.text()).toContain('Test String Value');

    expect(element.find('grr-semantic-value').length).toBe(2);
  });

});
