'use strict';

goog.require('grrUi.semantic.rekall.module');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');

describe('Rekall JSON directive', function() {
  var $compile, $rootScope;

  beforeEach(module(
      '/static/angular-components/semantic/rekall/rekall-json.html'));
  beforeEach(module(grrUi.semantic.rekall.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrRekallLog');
  grrUi.tests.stubDirective('grrRekallMetadata');
  grrUi.tests.stubDirective('grrRekallTable');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(
      jsonContextMessages, compressedJsonMessages) {
    $rootScope.jsonContextMessages = {'value': jsonContextMessages};
    $rootScope.compressedJsonMessages = {'value': compressedJsonMessages};

    var template =
        '<grr-rekall-json ' +
        '    json-context-messages="jsonContextMessages" ' +
        '    compressed-json-messages="compressedJsonMessages">' +
        '</grr-rekall-json>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when the input is empty', function() {
    var element = renderTestTemplate('[]', '[]');

    expect(element.find('div').length).toBe(0);
  });

  it('shows messages of known types.', function() {
    var element = renderTestTemplate(
        '[["t", {}]]', '[["L", {}], ["m", {}], ["r", {}]]');

    expect(element.find('div').length).toBe(3);
    expect(element.find('grr-rekall-log').length).toBe(1);
    expect(element.find('grr-rekall-metadata').length).toBe(1);
    expect(element.find('grr-rekall-table').length).toBe(1);
  });

  it('shows EOM for messages of type "x".', function() {
    var element = renderTestTemplate('[]', '[["x", {}]]');

    expect(element.find('div').length).toBe(1);
    expect(element.text()).toContain('EOM');
  });

  it('shows its input for messages of unknown type.', function() {
    var element = renderTestTemplate('[]', '[["?", {}]]');

    expect(element.find('div').length).toBe(1);
    expect(element.text()).toContain('["?",{}]');
  });

});
