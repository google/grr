'use strict';

goog.require('grrUi.client.module');
goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('grr-flow-id directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/semantic/flow-id.html'));
  beforeEach(module(grrUi.client.module.name));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value, clientId) {
    $rootScope.value = value;

    var template = '<grr-flow-id value="value"></grr-flow-id>';
    if (clientId) {
      $rootScope.clientId = clientId;
      template = '<grr-client-context client-id="clientId">' +
          template + '</grr-client-context>';
    }
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  var sampleValue = {
    value: 'F:112233',
    type: 'ApiFlowId'
  };

  describe('without client context', function() {

    it('renders flow id as a string', function() {
      var element = renderTestTemplate(sampleValue);
      expect(element.find('span:contains("F:112233")').length).toBe(1);
      expect(element.find('a:contains("F:112233")').length).toBe(0);
    });

  });

  describe('with client context', function() {

    it('renders flow id as a link', function() {
      var element = renderTestTemplate(sampleValue, 'C.1111222233334444');
      expect(element.find('span:contains("F:112233")').length).toBe(0);

      var aRef = element.find('a:contains("F:112233")');
      expect(aRef.length).toBe(1);
      expect(aRef.attr('href')).toBe(
          '#!/clients/C.1111222233334444/flows/F%3A112233');
    });

    it('renders a tooltip with a client id', function() {
      var element = renderTestTemplate(sampleValue, 'C.1111222233334444');
      var aref = element.find('a:contains("F:112233")');
      expect(aref.attr('title')).toBe('Flow F:112233 ran on client C.1111222233334444');
    });
  });
});
