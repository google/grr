'use strict';

goog.module('grrUi.artifact.artifactsListFormDirectiveTest');

const {artifactModule} = goog.require('grrUi.artifact.artifact');
const {browserTriggerEvent, stubDirective, testsModule} = goog.require('grrUi.tests');


describe('artifacts list form directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrArtifactDescriptorsService;

  let descriptorDarwinWindows;
  let descriptorLinux;


  beforeEach(module('/static/angular-components/artifact/artifacts-list-form.html'));
  beforeEach(module(artifactModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrSemanticValue');

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrArtifactDescriptorsService = $injector.get('grrArtifactDescriptorsService');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;
    $rootScope.descriptor = {
      default: {
        type: 'ArtifactName',
        value: '',
      },
    };

    const template = '<grr-artifacts-list-form descriptor="descriptor" ' +
        'value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows "Loading artifacts..." while artifacts are being loaded', () => {
    const deferred = $q.defer();
    spyOn(grrArtifactDescriptorsService, 'listDescriptors').and
        .returnValue(deferred.promise);

    const element = renderTestTemplate([]);
    expect(element.text()).toContain('Loading artifacts...');
  });

  describe('when descriptors listing fails', () => {
    beforeEach(() => {
      spyOn(grrArtifactDescriptorsService, 'listDescriptors')
          .and.callFake(() => {
            const deferred = $q.defer();
            deferred.reject('Oh no!');
            return deferred.promise;
          });
    });

    it('hides "Loading artifacts..." message', () => {
      const element = renderTestTemplate([]);

      expect(element.text()).not.toContain('Loading artifacts...');
    });

    it('shows a failure message on artifacts fetch failure', () => {
      const element = renderTestTemplate([]);

      expect(element.text()).toContain('Oh no!');
    });
  });

  describe('when descriptors listing succeeds', () => {
    beforeEach(() => {
      descriptorLinux = {
        type: 'ArtifactDescriptor',
        value: {
          artifact: {
            type: 'Artifact',
            value: {
              name: {type: 'ArtifactName', value: 'FooLinux'},
              supported_os: [
                {type: 'RDFString', value: 'Linux'},
              ],
            },
          },
        },
      };

      descriptorDarwinWindows = {
        type: 'ArtifactDescriptor',
        value: {
          artifact: {
            type: 'Artifact',
            value: {
              name: {type: 'ArtifactName', value: 'BarDarwinWindows'},
              supported_os: [
                {type: 'RDFString', value: 'Darwin'},
                {type: 'RDFString', value: 'Windows'},
              ],
            },
          },
        },
      };

      spyOn(grrArtifactDescriptorsService, 'listDescriptors')
          .and.callFake(() => {
            const deferred = $q.defer();
            deferred.resolve({
              'FooLinux': descriptorLinux,
              'BarDarwinWindows': descriptorDarwinWindows,
            });
            return deferred.promise;
          });
    });

    it('hides "Loading artifacts..." message', () => {
      const element = renderTestTemplate([]);

      expect(element.text()).not.toContain('Loading artifacts...');
    });

    it('shows all artifacts for selection by default', () => {
      const element = renderTestTemplate([]);

      expect(element.text()).toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');
    });

    it('prefills selection list from model', () => {
      const element =
          renderTestTemplate([{type: 'ArtifactName', value: 'FooLinux'}]);

      expect(element.find('table[name=SelectedArtifacts] ' +
          'tr:contains("FooLinux")').length).toBe(1);
    });

    it('filters artifacts by platform', () => {
      const element = renderTestTemplate([]);

      browserTriggerEvent(element.find('a:contains("Darwin")'), 'click');
      expect(element.text()).not.toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');

      browserTriggerEvent(element.find('a:contains("Windows")'), 'click');
      expect(element.text()).not.toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');

      browserTriggerEvent(element.find('a:contains("Linux")'), 'click');
      expect(element.text()).toContain('FooLinux');
      expect(element.text()).not.toContain('BarDarwinWindows');
    });

    it('checks sources platform when filtering by platform', () => {
      descriptorLinux = {
        type: 'ArtifactDescriptor',
        value: {
          artifact: {
            type: 'Artifact',
            value: {
              name: {type: 'ArtifactName', value: 'FooLinux'},
              sources: [
                {
                  type: 'ArtifactSource',
                  value: {
                    supported_os: [
                      {type: 'RDFString', value: 'Linux'},
                    ],
                  },
                },
              ],
            },
          },
        },
      };

      descriptorDarwinWindows = {
        type: 'ArtifactDescriptor',
        value: {
          artifact: {
            type: 'Artifact',
            value: {
              name: {type: 'ArtifactName', value: 'BarDarwinWindows'},
              sources: [
                {
                  type: 'ArtifactSource',
                  value: {
                    supported_os: [
                      {type: 'RDFString', value: 'Darwin'},
                      {type: 'RDFString', value: 'Windows'},
                    ],
                  },
                },
              ],
            },
          },
        },
      };

      const element = renderTestTemplate([]);
      browserTriggerEvent(element.find('a:contains("Darwin")'), 'click');
      expect(element.text()).not.toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');

      browserTriggerEvent(element.find('a:contains("Windows")'), 'click');
      expect(element.text()).not.toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');

      browserTriggerEvent(element.find('a:contains("Linux")'), 'click');
      expect(element.text()).toContain('FooLinux');
      expect(element.text()).not.toContain('BarDarwinWindows');
    });

    it('filters artifacts by name', () => {
      const element = renderTestTemplate([]);

      element.find('input[name=Search]').val('bar');
      browserTriggerEvent(element.find('input[name=Search]'), 'change');
      $rootScope.$apply();

      expect(element.text()).not.toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');
    });

    it('shows artifact descriptor info for selected artifact', () => {
      const element = renderTestTemplate([]);

      let infoDirective;
      browserTriggerEvent(element.find('td:contains("FooLinux")'), 'click');
      infoDirective = element.find('grr-semantic-value');
      expect(infoDirective.scope().$eval(infoDirective.attr('value'))).toEqual(
          descriptorLinux);

      browserTriggerEvent(element.find('td:contains("BarDarwinWindows")'), 'click');
      infoDirective = element.find('grr-semantic-value');
      expect(infoDirective.scope().$eval(infoDirective.attr('value'))).toEqual(
          descriptorDarwinWindows);
    });

    it('picks the artifact when Add is pressed', () => {
      const element = renderTestTemplate([]);

      browserTriggerEvent(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")'), 'click');
      browserTriggerEvent(element.find('button:contains("Add")'), 'click');

      expect(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")').length).toBe(0);
      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")').length).toBe(1);
    });

    it('picks the artifact on double click', () => {
      const element = renderTestTemplate([]);

      browserTriggerEvent(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")'), 'dblclick');

      expect(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")').length).toBe(0);
      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")').length).toBe(1);
    });

    it('updates the model when artifact is picked', () => {
      const element = renderTestTemplate([]);

      browserTriggerEvent(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")'), 'dblclick');

      expect(angular.equals($rootScope.value,
                            [{type: 'ArtifactName', value: 'FooLinux'}]));
    });

    it('unpicks the artifact when Remove is pressed', () => {
      const element =
          renderTestTemplate([{type: 'ArtifactName', value: 'FooLinux'}]);

      browserTriggerEvent(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")'), 'click');
      browserTriggerEvent(element.find('button:contains("Remove")'), 'click');

      expect(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")').length).toBe(1);
      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")').length).toBe(0);
    });

    it('unpicks the artifact on double click', () => {
      const element =
          renderTestTemplate([{type: 'ArtifactName', value: 'FooLinux'}]);

      browserTriggerEvent(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")'), 'dblclick');

      expect(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")').length).toBe(1);
      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")').length).toBe(0);
    });

    it('updates the model when artifact is unpicked', () => {
      const element =
          renderTestTemplate([{type: 'ArtifactName', value: 'FooLinux'}]);

      browserTriggerEvent(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")'), 'dblclick');

      expect(angular.equals($rootScope.value, []));
    });

    it('clears list of picked artifacts when Clear is pressed', () => {
      const element = renderTestTemplate([
        {type: 'ArtifactName', value: 'FooLinux'},
        {type: 'ArtifactName', value: 'BarDarwinWindows'}
      ]);

      browserTriggerEvent(element.find('button:contains("Clear")'), 'click');

      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")').length).toBe(0);
      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("BarDarwinWindows")').length).toBe(0);
    });

    it('updates the model when selection list is cleared', () => {
      const element = renderTestTemplate([
        {type: 'ArtifactName', value: 'FooLinux'},
        {type: 'ArtifactName', value: 'BarDarwinWindows'}
      ]);

      browserTriggerEvent(element.find('button:contains("Clear")'), 'click');

      expect(angular.equals($rootScope.value, []));
    });
  });
});


exports = {};
