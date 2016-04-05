'use strict';

goog.require('grrUi.hunt.newHuntWizard.module');
goog.require('grrUi.tests.module');

describe('grr-configure-deprecated-rules-page new hunt wizard directive', function() {
  var $compile, $rootScope, $q, grrApiService, grrReflectionService;

  beforeEach(module('/static/angular-components/hunt/new-hunt-wizard/' +
      'configure-deprecated-rules-page.html'));
  beforeEach(module(grrUi.hunt.newHuntWizard.module.name));
  beforeEach(module(grrUi.tests.module.name));

  // Stub out grr-form-value directive, as rules forms rendering is delegated
  // to it.
  grrUi.tests.stubDirective('grrFormValue');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    grrReflectionService = $injector.get('grrReflectionService');

    spyOn(grrReflectionService, 'getRDFValueDescriptor').and.callFake(
        function(name) {
          var deferred = $q.defer();

          if (name == 'ForemanAttributeRegex') {
            deferred.resolve({
              default: {
                type: 'ForemanAttributeRegex',
                value: {}
              }
            });
          } else if (name == 'ForemanAttributeInteger') {
            deferred.resolve({
              default: {
                type: 'ForemanAttributeInteger',
                value: {}
              }
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

  var renderTestTemplate = function(regexRules, integerRules) {
    if (angular.isUndefined(regexRules)) {
      regexRules = [];
    }

    if (angular.isUndefined(integerRules)) {
      integerRules = [];
    }

    $rootScope.regexRules = regexRules;
    $rootScope.integerRules = integerRules;

    var template = '<grr-configure-deprecated-rules-page ' +
        'regex-rules="regexRules" integer-rules="integerRules" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('adds one "Windows" rule if rules list is empty', function() {
    var element = renderTestTemplate();

    // Check that default Windows rule is shown.
    expect(element.text()).toContain(
        'This rule will match all Windows systems');

    // Check that default Windows rule is in the model.
    expect($rootScope.regexRules.length).toBe(1);
    expect($rootScope.regexRules[0].value.attribute_name.value)
        .toBe('System');
    expect($rootScope.regexRules[0].value.attribute_regex.value)
        .toBe('Windows');
  });

  it('keeps rules list as it is if it\'s not empty', function() {
    var regexRules = [
      {
        type: 'ForemanAttributeRegex',
        value: {
          attribute_name: {
            type: 'RDFString',
            value: 'System'
          },
          attribute_regex: {
            type: 'RegularExpression',
            value: 'BeOS'
          }
        }
      }
    ];
    var element = renderTestTemplate(angular.copy(regexRules));

    // Check that default Windows rule is not shown.
    expect(element.text()).not.toContain(
        'This rule will match all Windows systems');

    // Check that model wasn't modified by the directive.
    expect($rootScope.regexRules).toEqual(regexRules);
  });

  it('removes rule when "x" is clicked', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button[name=Remove]'), 'click');

    expect($rootScope.regexRules.length).toBe(0);
    expect($rootScope.integerRules.length).toBe(0);
  });

  it('adds "Windows" rule when "Add" is clicked', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button[name=Remove]'), 'click');
    browserTrigger(element.find('button[name=Add]'), 'click');

    expect($rootScope.regexRules.length).toBe(1);
    expect($rootScope.regexRules[0].value.attribute_name.value)
        .toBe('System');
    expect($rootScope.regexRules[0].value.attribute_regex.value)
        .toBe('Windows');
  });

  it('adds "Linux" rule as a regex rule', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button[name=Remove]'), 'click');
    browserTrigger(element.find('button[name=Add]'), 'click');
    element.find('select').val(
        element.find('select option[label="Linux"]').val());
    browserTrigger(element.find('select'), 'change');

    expect($rootScope.regexRules.length).toBe(1);
    expect($rootScope.regexRules[0].value.attribute_name.value)
        .toBe('System');
    expect($rootScope.regexRules[0].value.attribute_regex.value)
        .toBe('Linux');
  });

  it('adds "OS X" rule as a regex rule', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button[name=Remove]'), 'click');
    browserTrigger(element.find('button[name=Add]'), 'click');
    element.find('select').val(
        element.find('select option[label="OS X"]').val());
    browserTrigger(element.find('select'), 'change');

    expect($rootScope.regexRules.length).toBe(1);
    expect($rootScope.regexRules[0].value.attribute_name.value)
        .toBe('System');
    expect($rootScope.regexRules[0].value.attribute_regex.value)
        .toBe('Darwin');
  });

  it('shows list of labels for "Clients With Label" rule', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button[name=Remove]'), 'click');
    browserTrigger(element.find('button[name=Add]'), 'click');
    element.find('select').val(
        element.find('select option[label="Clients With Label"]').val());
    browserTrigger(element.find('select'), 'change');

    expect(element.find('select[name=Labels] option').length).toBe(2);
    expect(element.find('select[name=Labels] option:nth(0)').attr('label'))
        .toBe('label_1');
    expect(element.find('select[name=Labels] option:nth(1)').attr('label'))
        .toBe('label_2');
  });

  it('updates regexp when selected label changes', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button[name=Remove]'), 'click');
    browserTrigger(element.find('button[name=Add]'), 'click');
    element.find('select').val(
        element.find('select option[label="Clients With Label"]').val());
    browserTrigger(element.find('select'), 'change');

    expect($rootScope.regexRules.length).toBe(1);
    expect($rootScope.regexRules[0].value.attribute_name.value)
        .toBe('Labels');
    expect($rootScope.regexRules[0].value.attribute_regex.value)
        .toBe('(.+,|\\A)' + 'label_1' + '(,.+|\\Z)');

    // Now select another label.
    element.find('select[name=Labels]').val(
        element.find('select[name=Labels] option[label="label_2"]').val());
    browserTrigger(element.find('select[name=Labels]'), 'change');
    expect($rootScope.regexRules[0].value.attribute_regex.value)
        .toBe('(.+,|\\A)' + 'label_2' + '(,.+|\\Z)');
  });

  it('recognizes Windows matching regex rule on init',
     function() {
    var regexRules = [
      {
        type: 'ForemanAttributeRegex',
        value: {
          attribute_name: {
            type: 'RDFString',
            value: 'System'
          },
          attribute_regex: {
            type: 'RegularExpression',
            value: 'Windows'
          }
        }
      }
    ];
    var element = renderTestTemplate(regexRules);
    expect(element.text()).toContain(
        'This rule will match all Windows systems');
  });

  it('recognizes OS X matching regex rule on init',
     function() {
    var regexRules = [
      {
        type: 'ForemanAttributeRegex',
        value: {
          attribute_name: {
            type: 'RDFString',
            value: 'System'
          },
          attribute_regex: {
            type: 'RegularExpression',
            value: 'Darwin'
          }
        }
      }
    ];
    var element = renderTestTemplate(regexRules);
    expect(element.text()).toContain(
        'This rule will match all OS X systems');
  });

  it('recognizes Linux matching regex rule on init',
     function() {
    var regexRules = [
      {
        type: 'ForemanAttributeRegex',
        value: {
          attribute_name: {
            type: 'RDFString',
            value: 'System'
          },
          attribute_regex: {
            type: 'RegularExpression',
            value: 'Linux'
          }
        }
      }
    ];
    var element = renderTestTemplate(regexRules);
    expect(element.text()).toContain(
        'This rule will match all Linux systems');
  });

  it('recognizes client label matching rule on init',
     function() {
    var regexRules = [
      {
        type: 'ForemanAttributeRegex',
        value: {
          attribute_name: {
            type: 'RDFString',
            value: 'Labels'
          },
          attribute_regex: {
            type: 'RegularExpression',
            value: '(.+,|\\A)' + 'label_2' + '(,.+|\\Z)'
          }
        }
      }
    ];
    var element = renderTestTemplate(regexRules);

    expect(element.find('select').val()).toBe(
        element.find('select option[label="Clients With Label"]').val());
  });

  it('delegates regex rule rendering to grr-form-value', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button[name=Remove]'), 'click');
    browserTrigger(element.find('button[name=Add]'), 'click');
    element.find('select').val(
        element.find('select option[label="Regular Expression"]').val());
    browserTrigger(element.find('select'), 'change');

    // Check that rendering is delegated to grr-form-value.
    var formValue = element.find('grr-form-value[name=RegexRuleForm]');
    expect(formValue.scope().$eval(formValue.attr('value'))).toEqual({
      type: 'ForemanAttributeRegex',
      value: {}
    });

    // Check that model is correctly updated.
    expect($rootScope.regexRules.length).toBe(1);
    expect($rootScope.regexRules[0].value).toEqual({});
  });

  it('delegates integer rule rendering to grr-form-value', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button[name=Remove]'), 'click');
    browserTrigger(element.find('button[name=Add]'), 'click');
    element.find('select').val(
        element.find('select option[label="Integer Rule"]').val());
    browserTrigger(element.find('select'), 'change');

    var formValue = element.find('grr-form-value[name=IntegerRuleForm]');
    expect(formValue.scope().$eval(formValue.attr('value'))).toEqual({
      type: 'ForemanAttributeInteger',
      value: {}
    });

    // Check that model is correctly updated.
    expect($rootScope.integerRules.length).toBe(1);
    expect($rootScope.integerRules[0].value).toEqual({});
  });

});
