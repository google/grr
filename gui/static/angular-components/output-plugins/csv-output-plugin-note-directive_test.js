'use strict';

goog.require('grrUi.outputPlugins.module');
goog.require('grrUi.tests.module');


describe('csv output plugin directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/output-plugins/' +
      'csv-output-plugin.html'));
  beforeEach(module('/static/angular-components/core/aff4-download-link.html'));
  beforeEach(module(grrUi.outputPlugins.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrAff4DownloadLink');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(state) {
    $rootScope.outputPlugin = {
      value: {
        state: state
      }
    };

    var template = '<grr-csv-output-plugin output-plugin="outputPlugin" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows "nothing was written yet" by default', function() {
    var element = renderTestTemplate({
      value: {
        output_streams: {}
      }
    });
    expect(element.text()).toContain('Nothing was written yet.');
  });

  it('shows download aff4-link for every written type', function() {
    var element = renderTestTemplate(
        {
          value: {
            output_base_urn: {
              value: 'aff4:/foo/bar'
            },
            output_streams: {
              value: {
                'ExportedFile': {},
                'ExportedClient': {}
              }
            }
          }
        });

    expect(element.text()).toContain('Following files were written');

    var links = [];
    element.find('grr-aff4-download-link').each(function(index, link) {
      links.push($(link).scope().$eval($(link).attr('aff4-path')));
    });
    links.sort();
    expect(links).toEqual([
      'aff4:/foo/bar/ExportedClient',
      'aff4:/foo/bar/ExportedFile'
    ]);
 });
});
