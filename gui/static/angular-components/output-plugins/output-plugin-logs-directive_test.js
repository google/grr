'use strict';

goog.require('grrUi.outputPlugins.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('output plugin logs directive', function() {
  var $q, $compile, $rootScope, $timeout, grrApiService;

  beforeEach(module('/static/angular-components/output-plugins/output-plugin-logs.html'));
  beforeEach(module('/static/angular-components/output-plugins/output-plugin-logs-modal.html'));
  beforeEach(module(grrUi.outputPlugins.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrPagedFilteredTable');

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $timeout = $injector.get('$timeout');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');

  }));

  var renderTestTemplate = function() {
    $rootScope.url = 'foo/bar';

    var template = '<grr-output-plugin-logs url="url" label="a foo"' +
        'css-class="label-danger" icon="foo-icon" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('fetches and show items count', function() {
    var deferred = $q.defer();
    deferred.resolve({
      data: {
        total_count: 42
      }
    });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    var element = renderTestTemplate();

    expect(element.text()).toContain('42');
  });

  it('shows nothing if total_count is 0', function() {
    var deferred = $q.defer();
    deferred.resolve({
      data: {
        total_count: 0
      }
    });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    var element = renderTestTemplate();

    expect(element.text().trim()).toBe('');
  });


  describe('inspect dialog', function() {

    beforeEach(function() {
      var deferred = $q.defer();
      deferred.resolve({
        data: {
          total_count: 42
        }
      });
      spyOn(grrApiService, 'get').and.returnValue(deferred.promise);
    });

    afterEach(function() {
      // We have to clean document's body to remove modal windows that were not
      // closed.
      $(document.body).html('');
    });

    it('is shown when label is clicked', function() {
      var element = renderTestTemplate();
      browserTrigger(element.find('.label'), 'click');

      expect($(document.body).text()).toContain(
          'Inspect a foo');
    });

    it('closes when close button is clicked', function() {
      var element = renderTestTemplate();
      browserTrigger(element.find('.label'), 'click');

      browserTrigger($('button.close'), 'click');
      $timeout.flush();
      expect($(document.body).text()).not.toContain(
          'Inspect a foo');
    });
  });
});
