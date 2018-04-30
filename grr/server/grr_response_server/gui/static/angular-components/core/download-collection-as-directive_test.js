'use strict';

goog.module('grrUi.core.downloadCollectionAsDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {coreModule} = goog.require('grrUi.core.core');


describe('"download collection as" panel', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;

  beforeEach(module('/static/angular-components/core/download-collection-as.html'));
  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  const renderTestTemplate = (baseUrl) => {
    $rootScope.baseUrl = baseUrl || 'foo/bar';

    const template = '<grr-download-collection-as ' +
        'base-url="baseUrl" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  const testDownloadAsType =
      ((plugin) => (() => {
         const deferred = $q.defer();
         spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

         const element = renderTestTemplate();
         element.find('#plugin-select').val(`string:${plugin}`).change();
         browserTriggerEvent(element.find('button[name="download-as"]'), 'click');

         expect(grrApiService.downloadFile)
             .toHaveBeenCalledWith(`foo/bar/${plugin}`);
       }));

  it('sends correct request for CSV download', testDownloadAsType('csv-zip'));

  it('sends correct request for flattened YAML download',
     testDownloadAsType('flattened-yaml-zip'));

  it('sends correct request for sqlite download',
      testDownloadAsType('sqlite-zip'));
});


exports = {};
