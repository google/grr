'use strict';

goog.require('grrUi.outputPlugins.module');
goog.require('grrUi.tests.module');


describe('output plugins notes list directive', function() {
  var $compile, $rootScope, $q, grrAff4Service;

  beforeEach(module('/static/angular-components/output-plugins/' +
        'output-plugins-notes.html'));
  beforeEach(module(grrUi.outputPlugins.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrAff4Service = $injector.get('grrAff4Service');
  }));

  var renderTestTemplate = function() {
    $rootScope.metadataUrn = 'aff4:/foo/bar';

    var template = '<grr-output-plugins-notes metadata-urn="metadataUrn" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('requests AFF4 metadata object via AFF4 service', function() {
    var deferred = $q.defer();
    spyOn(grrAff4Service, 'get').and.returnValue(deferred.promise);

    var element = renderTestTemplate();

    expect(grrAff4Service.get).toHaveBeenCalledWith(
        'aff4:/foo/bar',
        {'AFF4Object.type_info': 'WITH_TYPES_AND_METADATA'});
  });

  it('shows an error when AFF4 request fails', function() {
    var deferred = $q.defer();
    spyOn(grrAff4Service, 'get').and.returnValue(deferred.promise);
    deferred.reject({data: {message: 'FAIL'}});

    var element = renderTestTemplate();
    expect(element.text()).toContain('Can\'t fetch output plugins metadata: ' +
        'FAIL');
  });

  it('delegates every plugin display to grr-output-plugin-note', function() {
    var deferred = $q.defer();
    spyOn(grrAff4Service, 'get').and.returnValue(deferred.promise);

    var descriptor1 = {
      value: {
        plugin_name: {
          value: 'plugin1'
        }
      }
    };
    var descriptor2 = {
      value: {
        plugin_name: {
          value: 'plugin2'
        }
      }
    };

    var state1 = {
      'foo': 'bar1'
    };
    var state2 = {
      'foo': 'bar2'
    };
    deferred.resolve({
      data: {
        attributes: {
          'aff4:output_plugins_state': {
            'Output1': [descriptor1, state1],
            'Output2': [descriptor2, state2]
          }
        }
      }
    });

    var element = renderTestTemplate();
    expect(element.find('grr-output-plugin-note').length).toBe(2);

    var directive = element.find('grr-output-plugin-note:nth(0)');
    expect(directive.scope().$eval(directive.attr('descriptor'))).toEqual(
        descriptor1);
    expect(directive.scope().$eval(directive.attr('state'))).toEqual(state1);

    directive = element.find('grr-output-plugin-note:nth(1)');
    expect(directive.scope().$eval(directive.attr('descriptor'))).toEqual(
        descriptor2);
    expect(directive.scope().$eval(directive.attr('state'))).toEqual(state2);
  });
});
