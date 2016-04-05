'use strict';

goog.require('grrUi.artifact.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('artifacts list form directive', function() {
  var $q, $compile, $rootScope, grrApiService;
  var descriptorLinux, descriptorDarwinWindows;

  beforeEach(module('/static/angular-components/artifact/artifacts-list-form.html'));
  beforeEach(module(grrUi.artifact.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrSemanticValue');

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;
    $rootScope.descriptor = {
      default: {
        type: 'ArtifactName',
        value: ''
      }
    };

    var template = '<grr-artifacts-list-form descriptor="descriptor" ' +
        'value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  describe('when API calls fail', function() {
    beforeEach(function() {
      spyOn(grrApiService, 'get').and.callFake(function() {
        var deferred = $q.defer();
        deferred.reject({
          data: {
            message: 'Oh no!'
          }
        });
        return deferred.promise;
      });
    });

    it('shows a failure message on artifacts fetch failure', function() {
      var element = renderTestTemplate([]);

      expect(element.text()).toContain('Oh no!');
    });
  });

  describe('when API calls succeed', function() {
    beforeEach(function() {
      descriptorLinux = {
        type: 'ArtifactDescriptor',
        value: {
          artifact: {
            type: 'Artifact',
            value: {
              name: {type: 'ArtifactName', value: 'FooLinux'},
              supported_os: [
                {type: 'RDFString', value: 'Linux'}
              ]
            }
          }
        }
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
                {type: 'RDFString', value: 'Windows'}
              ]
            }
          }
        }
      };

      spyOn(grrApiService, 'get').and.callFake(function() {
        var deferred = $q.defer();
        deferred.resolve({
          data: {
            items: [
              descriptorLinux,
              descriptorDarwinWindows
            ]
          }
        });
        return deferred.promise;
      });
    });

    it('shows all artifacts for selection by default', function() {
      var element = renderTestTemplate([]);

      expect(element.text()).toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');
    });

    it('prefills selection list from model', function() {
      var element = renderTestTemplate(
          [{type: 'ArtifactName', value: 'FooLinux'}]);

      expect(element.find('table[name=SelectedArtifacts] ' +
          'tr:contains("FooLinux")').length).toBe(1);
    });

    it('filters artifacts by platform', function() {
      var element = renderTestTemplate([]);

      browserTrigger(element.find('a:contains("Darwin")'), 'click');
      expect(element.text()).not.toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');

      browserTrigger(element.find('a:contains("Windows")'), 'click');
      expect(element.text()).not.toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');

      browserTrigger(element.find('a:contains("Linux")'), 'click');
      expect(element.text()).toContain('FooLinux');
      expect(element.text()).not.toContain('BarDarwinWindows');
    });

    it('checks sources platform when filtering by platform', function() {
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
                      {type: 'RDFString', value: 'Linux'}
                    ]
                  }
                }
              ]
            }
          }
        }
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
                      {type: 'RDFString', value: 'Windows'}
                    ]
                  }
                }
              ]
            }
          }
        }
      };

      var element = renderTestTemplate([]);
      browserTrigger(element.find('a:contains("Darwin")'), 'click');
      expect(element.text()).not.toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');

      browserTrigger(element.find('a:contains("Windows")'), 'click');
      expect(element.text()).not.toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');

      browserTrigger(element.find('a:contains("Linux")'), 'click');
      expect(element.text()).toContain('FooLinux');
      expect(element.text()).not.toContain('BarDarwinWindows');
    });

    it('filters artifacts by name', function() {
      var element = renderTestTemplate([]);

      element.find('input[name=Search]').val('bar');
      browserTrigger(element.find('input[name=Search]'), 'change');
      $rootScope.$apply();

      expect(element.text()).not.toContain('FooLinux');
      expect(element.text()).toContain('BarDarwinWindows');
    });

    it('shows artifact descriptor info for selected artifact', function() {
      var element = renderTestTemplate([]);

      var infoDirective;
      browserTrigger(element.find('td:contains("FooLinux")'), 'click');
      infoDirective = element.find('grr-semantic-value');
      expect(infoDirective.scope().$eval(infoDirective.attr('value'))).toEqual(
          descriptorLinux);

      browserTrigger(element.find('td:contains("BarDarwinWindows")'), 'click');
      infoDirective = element.find('grr-semantic-value');
      expect(infoDirective.scope().$eval(infoDirective.attr('value'))).toEqual(
          descriptorDarwinWindows);
    });

    it('picks the artifact when Add is pressed', function() {
      var element = renderTestTemplate([]);

      browserTrigger(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")'), 'click');
      browserTrigger(element.find('button:contains("Add")'), 'click');

      expect(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")').length).toBe(0);
      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")').length).toBe(1);
    });

    it('picks the artifact on double click', function() {
      var element = renderTestTemplate([]);

      browserTrigger(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")'), 'dblclick');

      expect(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")').length).toBe(0);
      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")').length).toBe(1);
    });

    it('updates the model when artifact is picked', function() {
      var element = renderTestTemplate([]);

      browserTrigger(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")'), 'dblclick');

      expect(angular.equals($rootScope.value,
                            [{type: 'ArtifactName', value: 'FooLinux'}]));
    });

    it('unpicks the artifact when Remove is pressed', function() {
      var element = renderTestTemplate(
          [{type: 'ArtifactName', value: 'FooLinux'}]);

      browserTrigger(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")'), 'click');
      browserTrigger(element.find('button:contains("Remove")'), 'click');

      expect(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")').length).toBe(1);
      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")').length).toBe(0);
    });

    it('unpicks the artifact on double click', function() {
      var element = renderTestTemplate(
          [{type: 'ArtifactName', value: 'FooLinux'}]);

      browserTrigger(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")'), 'dblclick');

      expect(element.find('table[name=Artifacts] ' +
          'td:contains("FooLinux")').length).toBe(1);
      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")').length).toBe(0);
    });

    it('updates the model when artifact is unpicked', function() {
      var element = renderTestTemplate(
          [{type: 'ArtifactName', value: 'FooLinux'}]);

      browserTrigger(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")'), 'dblclick');

      expect(angular.equals($rootScope.value, []));
    });

    it('clears list of picked artifacts when Clear is pressed', function() {
      var element = renderTestTemplate(
          [{type: 'ArtifactName', value: 'FooLinux'},
           {type: 'ArtifactName', value: 'BarDarwinWindows'}]);

      browserTrigger(element.find('button:contains("Clear")'), 'click');

      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("FooLinux")').length).toBe(0);
      expect(element.find('table[name=SelectedArtifacts] ' +
          'td:contains("BarDarwinWindows")').length).toBe(0);
    });

    it('updates the model when selection list is cleared', function() {
      var element = renderTestTemplate(
          [{type: 'ArtifactName', value: 'FooLinux'},
           {type: 'ArtifactName', value: 'BarDarwinWindows'}]);

      browserTrigger(element.find('button:contains("Clear")'), 'click');

      expect(angular.equals($rootScope.value, []));
    });

  });

});
