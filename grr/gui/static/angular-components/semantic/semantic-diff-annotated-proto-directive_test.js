'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('grr-semantic-diff-annotated-proto directive', function() {
  var $compile, $rootScope, $q, grrReflectionService;

  beforeEach(module('/static/angular-components/semantic/semantic-diff-annotated-proto.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');

    grrReflectionService = $injector.get('grrReflectionService');
    spyOn(grrReflectionService, 'getRDFValueDescriptor');

    var descriptors = {
      'Bar': {},
      'Foo': {
        fields: [
          {
            name: 'a'
          }
        ]
      }
    };
    grrReflectionService.getRDFValueDescriptor.and.callFake(
          function(typeName) {
            var deferred = $q.defer();
            deferred.resolve(descriptors[typeName]);
            return deferred.promise;
          });
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-semantic-diff-annotated-proto value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };


  angular.forEach(['added', 'changed', 'removed'], function(annotation) {
    it('renders "' + annotation + '" annotation on the value itself correctly', function() {
      var value = {
        type: 'Foo',
        value: 42,
        _diff: annotation
      };

      var element = renderTestTemplate(value);
      expect(element.find('table.diff-' + annotation).length).toBe(1);
    });

    it('renders "' + annotation + '"-annotated non-repeated field correctly', function() {
      var value = {
        type: 'Foo',
        value: {
          a: {
            type: 'Bar',
            value: 42,
            _diff: annotation
          }
        }
      };

      var element = renderTestTemplate(value);
      expect(element.find('tr.diff-' + annotation).length).toBe(1);
    });

    it('renders "' + annotation + '"-annotated repeated field correctly', function() {
      var value = {
        type: 'Foo',
        value: {
          a: [
            {
              type: 'Bar',
              value: 42,
              _diff: annotation
            }
          ]
        }
      };

      var element = renderTestTemplate(value);
      expect(element.find('div.repeated.diff-' + annotation).length).toBe(1);
    });
  });
});
