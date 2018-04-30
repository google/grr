'use strict';

goog.module('grrUi.artifact.artifactNameDirectiveTest');

const {artifactModule} = goog.require('grrUi.artifact.artifact');
const {testsModule} = goog.require('grrUi.tests');


describe('grr-artifact-name directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrArtifactDescriptorsService;


  beforeEach(module('/static/angular-components/artifact/artifact-name.html'));
  beforeEach(module(artifactModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrArtifactDescriptorsService = $injector.get('grrArtifactDescriptorsService');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-artifact-name value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  const systemDescriptor = {
    type: 'ArtifactDescriptor',
    value: {
      artifact: {
        value: {
          name: {
            value: 'foo',
          },
        },
      },
      is_custom: {
        value: false,
      },
    },
  };

  const userDescriptor = {
    type: 'ArtifactDescriptor',
    value: {
      artifact: {
        value: {
          name: {
            value: 'foo',
          },
        },
      },
      is_custom: {
        value: true,
      },
    },
  };

  it('shows artifact name as a string before it\'s resolved', () => {
    const deferred = $q.defer();
    spyOn(grrArtifactDescriptorsService, 'getDescriptorByName')
        .and.returnValue(deferred.promise);

    const element = renderTestTemplate({
      value: 'foo',
    });
    expect($('span.system', element).length).toBe(0);
    expect($('span.user', element).length).toBe(0);
    expect($('span.icon', element).length).toBe(0);
    expect(element.text()).toContain('foo');
  });

  it('marks system artifacts with .system class and no icon', () => {
    const deferred = $q.defer();
    deferred.resolve(systemDescriptor);
    spyOn(grrArtifactDescriptorsService, 'getDescriptorByName')
        .and.returnValue(deferred.promise);

    const element = renderTestTemplate({
      value: 'foo',
    });
    expect($('span.system', element).length).toBe(1);
    expect($('span.user', element).length).toBe(0);
    expect($('span.icon', element).length).toBe(0);
    expect(element.text()).toContain('foo');
  });

  it('marks user artifacts with .user class and an icon', () => {
    const deferred = $q.defer();
    deferred.resolve(userDescriptor);
    spyOn(grrArtifactDescriptorsService, 'getDescriptorByName')
        .and.returnValue(deferred.promise);

    const element = renderTestTemplate({
      value: 'foo',
    });
    expect($('span.system', element).length).toBe(0);
    expect($('span.user', element).length).toBe(1);
    expect(element.text()).toContain('foo');
  });

  it('does not mark unknown artifacts', () => {
    const deferred = $q.defer();
    deferred.resolve(undefined);
    spyOn(grrArtifactDescriptorsService, 'getDescriptorByName')
        .and.returnValue(deferred.promise);

    const element = renderTestTemplate({
      value: 'foo',
    });
    expect($('span.system', element).length).toBe(0);
    expect($('span.user', element).length).toBe(0);
    expect($('span.icon', element).length).toBe(0);
    expect(element.text()).toContain('foo');
  });
});


exports = {};
