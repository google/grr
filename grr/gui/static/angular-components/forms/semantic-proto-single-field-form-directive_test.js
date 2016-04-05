'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('semantic proto single field form directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/forms/semantic-proto-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-union-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-single-field-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-repeated-field-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value, field) {
    $rootScope.value = value;
    $rootScope.field = field;

    var template = '<grr-form-proto-single-field value="value" ' +
        'field="field" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('renders doc and friendly name', function() {
    var element = renderTestTemplate({}, {
      doc: 'Field documentation',
      friendly_name: 'Field friendly name'
    });

    expect(element.find('label[title="Field documentation"]').length).toBe(1);
    expect(element.text()).toContain('Field friendly name');
  });

  it('delegates rendering to grr-form-value', function() {
    var element = renderTestTemplate({}, {});

    expect(element.find('grr-form-value').length).toBe(1);
  });
});
