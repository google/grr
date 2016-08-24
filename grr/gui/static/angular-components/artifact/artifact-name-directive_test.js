'use strict';

goog.require('grrUi.artifact.module');
goog.require('grrUi.tests.module');

describe('grr-artifact-name directive', function() {
  var $compile, $rootScope, $q, grrArtifactDescriptorsService;

  beforeEach(module('/static/angular-components/artifact/artifact-name.html'));
  beforeEach(module(grrUi.artifact.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrArtifactDescriptorsService = $injector.get('grrArtifactDescriptorsService');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-artifact-name value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  var systemDescriptor = {
    type: 'ArtifactDescriptor',
    value: {
      artifact: {
        value: {
          name: {
            value: 'foo'
          }
        }
      },
      is_custom: {
        value: false
      }
    }
  };

  var userDescriptor = {
    type: 'ArtifactDescriptor',
    value: {
      artifact: {
        value: {
          name: {
            value: 'foo'
          }
        }
      },
      is_custom: {
        value: true
      }
    }
  };

  it('shows artifact name as a string before it\'s resolved', function() {
    var deferred = $q.defer();
    spyOn(grrArtifactDescriptorsService, 'getDescriptorByName')
        .and.returnValue(deferred.promise);

    var element = renderTestTemplate({
      value: 'foo'
    });
    expect($('span.system', element).length).toBe(0);
    expect($('span.user', element).length).toBe(0);
    expect($('span.icon', element).length).toBe(0);
    expect(element.text()).toContain('foo');
  });

  it('marks system artifacts with .system class and no icon', function() {
    var deferred = $q.defer();
    deferred.resolve(systemDescriptor);
    spyOn(grrArtifactDescriptorsService, 'getDescriptorByName')
        .and.returnValue(deferred.promise);

    var element = renderTestTemplate({
      value: 'foo'
    });
    expect($('span.system', element).length).toBe(1);
    expect($('span.user', element).length).toBe(0);
    expect($('span.icon', element).length).toBe(0);
    expect(element.text()).toContain('foo');
  });

  it('marks user artifacts with .user class and an icon', function() {
    var deferred = $q.defer();
    deferred.resolve(userDescriptor);
    spyOn(grrArtifactDescriptorsService, 'getDescriptorByName')
        .and.returnValue(deferred.promise);

    var element = renderTestTemplate({
      value: 'foo'
    });
    expect($('span.system', element).length).toBe(0);
    expect($('span.user', element).length).toBe(1);
    expect(element.text()).toContain('foo');
  });

  it('does not mark unknown artifacts', function() {
    var deferred = $q.defer();
    deferred.resolve(undefined);
    spyOn(grrArtifactDescriptorsService, 'getDescriptorByName')
        .and.returnValue(deferred.promise);

    var element = renderTestTemplate({
      value: 'foo'
    });
    expect($('span.system', element).length).toBe(0);
    expect($('span.user', element).length).toBe(0);
    expect($('span.icon', element).length).toBe(0);
    expect(element.text()).toContain('foo');
  });
});
