'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('semantic enum form directive', function() {
  var $compile, $rootScope, value;

  beforeEach(module('/static/angular-components/forms/semantic-enum-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');

    value = {age: 0,
             type: 'EnumNamedValue',
             value: 'NONE',
             mro: ['EnumNamedValue',
                   'RDFInteger',
                   'RDFString',
                   'RDFBytes',
                   'RDFValue',
                   'object']
            };
  }));

  var renderTestTemplate = function(metadata) {
    $rootScope.value = value;
    $rootScope.metadata = metadata;

    var template = '<grr-form-enum metadata="metadata" value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows list of options from the metadata', function() {
    var element = renderTestTemplate(
        {
          allowed_values: [
            { name: 'NONE', value: 0 },
            { name: 'CHOICE 1', value: 1 },
            { name: 'CHOICE 2', value: 2 }
          ]
        });

    expect(element.find('option').length).toBe(3);
    expect(element.find('option:nth(0)').attr('label')).toBe('NONE');
    expect(element.find('option:nth(1)').attr('label')).toBe('CHOICE 1');
    expect(element.find('option:nth(2)').attr('label')).toBe('CHOICE 2');
  });

  it('marks the default value with "(default)"', function() {
    var element = renderTestTemplate(
        {
          allowed_values: [
            { name: 'NONE', value: 0 },
            { name: 'CHOICE 1', value: 1 },
            { name: 'CHOICE 2', value: 2 }
          ],
          default: {'age': 0,
                    'type': 'EnumNamedValue',
                    'value': 'CHOICE 1',
                    'mro': ['EnumNamedValue',
                            'RDFInteger',
                            'RDFString',
                            'RDFBytes',
                            'RDFValue',
                            'object']},
        });

    expect(element.find('option').length).toBe(3);
    expect(element.find('option:nth(0)').attr('label')).toBe('NONE');
    expect(element.find('option:nth(1)').attr('label')).toBe(
        'CHOICE 1 (default)');
    expect(element.find('option:nth(2)').attr('label')).toBe('CHOICE 2');
  });

  it('updates the value when user selects an option', function() {
    var element = renderTestTemplate(
        {
          allowed_values: [
            { name: 'NONE', value: 0 },
            { name: 'CHOICE 1', value: 1 },
            { name: 'CHOICE 2', value: 2 }
          ]
        });

    expect(value.value).toBe('NONE');

    element.find('select').val(
        element.find('select option[label="CHOICE 2"]').val());
    browserTrigger(element.find('select'), 'change');
    $rootScope.$apply();

    expect(value.value).toBe('CHOICE 2');
  });
});
