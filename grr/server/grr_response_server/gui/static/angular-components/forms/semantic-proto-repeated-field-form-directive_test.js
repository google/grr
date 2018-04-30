'use strict';

goog.module('grrUi.forms.semanticProtoRepeatedFieldFormDirectiveTest');

const {browserTriggerEvent, stubDirective, testsModule} = goog.require('grrUi.tests');
const {formsModule} = goog.require('grrUi.forms.forms');


describe('semantic proto repeated field form directive', () => {
  let $compile;
  let $q;
  let $rootScope;

  beforeEach(module('/static/angular-components/forms/semantic-proto-repeated-field-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  // Stub out grrFormValue directive, as all rendering is going to be
  // delegated to it.
  stubDirective('grrFormValue');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
  }));

  const renderTestTemplate = (value, descriptor, field, noCustomTemplate) => {
    $rootScope.value = value;
    $rootScope.descriptor = descriptor;
    $rootScope.field = field;
    $rootScope.noCustomTemplate = noCustomTemplate;

    const template = '<grr-form-proto-repeated-field value="value" ' +
        'descriptor="descriptor" field="field" ' +
        'no-custom-template="noCustomTemplate" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  const typedPrimitiveValue = {
    type: 'PrimitiveType',
    value: 42,
  };

  const primitiveValueDescriptor = {
    type: 'PrimitiveType',
    mro: ['PrimitiveType'],
    kind: 'primitive',
    default: angular.copy(typedPrimitiveValue),
  };

  describe('without custom directives', () => {
    beforeEach(inject(($injector) => {
      // Always return false here - i.e. no custom directives are registered for
      // repeated fields.
      const grrSemanticRepeatedFormDirectivesRegistryService =
          $injector.get('grrSemanticRepeatedFormDirectivesRegistryService');

      spyOn(
          grrSemanticRepeatedFormDirectivesRegistryService,
          'findDirectiveForType')
          .and.callFake((type) => {
            const q = $q.defer();
            q.reject();

            return q.promise;
          });
    }));

    it('renders doc and friendly name', () => {
      const element = renderTestTemplate([], primitiveValueDescriptor, {
        doc: 'Field documentation',
        friendly_name: 'Field friendly name',
      });

      expect(element.find('label[title="Field documentation"]').length)
          .not.toBe(0);
      expect(element.text()).toContain('Field friendly name');
    });

    it('delegates items rendering to grr-form-value', () => {
      const element = renderTestTemplate(
          [
            {type: 'PrimitiveType', value: 42},
            {type: 'PrimitiveType', value: 43}
          ],
          primitiveValueDescriptor, {});

      expect(element.find('grr-form-value').length).toBe(2);
    });

    it('adds new item when "Add" is clicked', () => {
      const value = [];

      const element = renderTestTemplate(value, primitiveValueDescriptor, {});
      expect(element.find('grr-form-value').length).toBe(0);

      browserTriggerEvent($('button[name=Add]', element), 'click');
      expect(element.find('grr-form-value').length).toBe(1);
      // Please see http://stackoverflow.com/a/26370331 on why we're using here
      // angular.equals() and not Jasmine's toEqual here.
      expect(angular.equals(value, [typedPrimitiveValue])).toBe(true);

      browserTriggerEvent($('button[name=Add]', element), 'click');
      expect(element.find('grr-form-value').length).toBe(2);
      expect(angular.equals(value, [typedPrimitiveValue,
                                    typedPrimitiveValue])).toBe(true);
    });

    it('removes an item when "Remove" is clicked', () => {
      const value = [
        angular.copy(typedPrimitiveValue), angular.copy(typedPrimitiveValue)
      ];

      const element = renderTestTemplate(value, primitiveValueDescriptor, {});
      expect(element.find('grr-form-value').length).toBe(2);

      browserTriggerEvent($('button[name=Remove]:nth(0)', element), 'click');
      expect(element.find('grr-form-value').length).toBe(1);
      expect(angular.equals(value, [typedPrimitiveValue])).toBe(true);

      browserTriggerEvent($('button[name=Remove]:nth(0)', element), 'click');
      expect(element.find('grr-form-value').length).toBe(0);
      expect(value).toEqual([]);
    });
  });

  describe('with custom directive', () => {
    beforeEach(inject(($injector) => {
      const grrSemanticRepeatedFormDirectivesRegistryService =
          $injector.get('grrSemanticRepeatedFormDirectivesRegistryService');

      spyOn(
          grrSemanticRepeatedFormDirectivesRegistryService,
          'findDirectiveForType')
          .and.callFake((type) => {
            const q = $q.defer();
            q.resolve({
              directive_name: 'fooBar',
            });

            return q.promise;
          });
    }));

    it('renders doc and friendly name', () => {
      const element = renderTestTemplate([], primitiveValueDescriptor, {
        doc: 'Field documentation',
        friendly_name: 'Field friendly name',
      });

      expect(element.find('label[title="Field documentation"]').length)
          .not.toBe(0);
      expect(element.text()).toContain('Field friendly name');
    });

    it('delegates items rendering to grr-form-value', () => {
      const element = renderTestTemplate([], primitiveValueDescriptor, {});

      expect(element.find('foo-bar').length).toBe(1);
    });

    it('ignores custom directive if no-custom-template binding is true', () => {
      const element = renderTestTemplate(
          [
            {type: 'PrimitiveType', value: 42},
            {type: 'PrimitiveType', value: 43}
          ],
          primitiveValueDescriptor, {}, true);

      // No custom directive should be present.
      expect(element.find('foo-bar').length).toBe(0);

      // Default rendering should be used instead.
      expect(element.find('grr-form-value').length).toBe(2);
    });
  });

  describe('with custom directive with "hideCustomTemplateLabel" set', () => {
    beforeEach(inject(($injector) => {
      const grrSemanticRepeatedFormDirectivesRegistryService =
          $injector.get('grrSemanticRepeatedFormDirectivesRegistryService');

      spyOn(
          grrSemanticRepeatedFormDirectivesRegistryService,
          'findDirectiveForType')
          .and.callFake((type) => {
            const q = $q.defer();
            q.resolve({
              directive_name: 'fooBar',
              hideCustomTemplateLabel: true,
            });

            return q.promise;
          });
    }));

    it('does not render custom field\'s label', () => {
      const element = renderTestTemplate([], primitiveValueDescriptor, {});

      expect(element.find('label[title="Field documentation"]').length)
          .toBe(0);
      expect(element.text()).not.toContain('Field friendly name');
      expect(element.find('foo-bar').length).toBe(1);
    });
  });
});


exports = {};
