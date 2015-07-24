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

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(state) {
    $rootScope.descriptor = {};
    $rootScope.state = state;

    var template = '<grr-csv-output-plugin descriptor="descriptor" ' +
        'state="state" />';
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

    var link = element.find('grr-aff4-download-link:contains("ExportedFile")');
    expect(link.scope().$eval(link.attr('aff4-path'))).toBe(
        'aff4:/foo/bar/ExportedFile');

    link = element.find('grr-aff4-download-link:contains("ExportedClient")');
    expect(link.scope().$eval(link.attr('aff4-path'))).toBe(
        'aff4:/foo/bar/ExportedClient');
 });
});
