'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('client urn directive', function() {
  var $q, $compile, $rootScope, $timeout, grrApiService;

  beforeEach(module('/static/angular-components/semantic/client-urn.html'));
  beforeEach(module('/static/angular-components/semantic/client-urn-modal.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $timeout = $injector.get('$timeout');
    grrApiService = $injector.get('grrApiService');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-client-urn value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does not show anything when value is empty', function() {
    var element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('');
  });

  it('shows string value', function() {
    var element = renderTestTemplate('aff4:/C.0000000000000001');
    expect(element.text()).toContain('C.0000000000000001');
  });

  it('shows value with type information', function() {
    var clientUrn = {
      age: 0,
      type: 'ClientURN',
      value: 'aff4:/C.0000000000000001'
    };
    var element = renderTestTemplate(clientUrn);
    expect(element.text()).toContain('C.0000000000000001');
  });

  describe('client urn summary modal dialog', function() {

    beforeEach(function() {
      grrApiService.get = function(urn, params) {
        expect(urn).toBe('clients/C.0000000000000001');

        return $q(function(resolve, reject) {
          resolve({
            data: {
              client: 'This is a summary'
            }
          });
        });
      };
    });

    afterEach(function() {
      // We have to clean document's body to remove modal windows that were not
      // closed.
      $(document.body).html('');
    });

    it('is shown when info button is clicked', function() {
      var element = renderTestTemplate('aff4:/C.0000000000000001');
      browserTrigger($('button', element), 'click');
      expect($(document.body).text()).toContain(
          'Client aff4:/C.0000000000000001');
    });

    it('closed when close button is clicked', function() {
      var element = renderTestTemplate('aff4:/C.0000000000000001');
      browserTrigger($('button', element), 'click');
      expect($(document.body).text()).toContain(
          'Client aff4:/C.0000000000000001');

      browserTrigger($('button.close'), 'click');
      $timeout.flush();
      expect($(document.body).text()).not.toContain(
          'Client aff4:/C.0000000000000001');
    });
  });
});
