'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('"download collection as" panel', function() {
  var $q, $compile, $rootScope, $timeout, grrApiService;

  var ERROR_EVENT_NAME =
      grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective
      .error_event_name;

  beforeEach(module('/static/angular-components/core/download-collection-as.html'));
  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  var renderTestTemplate = function(baseUrl) {
    $rootScope.baseUrl = baseUrl || 'foo/bar';

    var template = '<grr-download-collection-as ' +
        'base-url="baseUrl" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  var testDownloadAsType = function(plugin) {
    return function() {
      var deferred = $q.defer();
      spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

      var element = renderTestTemplate();
      element.find('#plugin-select').val('string:' + plugin).change();
      browserTrigger(element.find('button[name="download-as"]'), 'click');

      expect(grrApiService.downloadFile).toHaveBeenCalledWith(
          'foo/bar/' + plugin);
    };
  };

  it('sends correct request for CSV download', testDownloadAsType('csv-zip'));

  it('sends correct request for flattened YAML download',
     testDownloadAsType('flattened-yaml-zip'));

  it('sends correct request for sqlite download',
      testDownloadAsType('sqlite-zip'));
});
