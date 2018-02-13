'use strict';

goog.module('grrUi.semantic.rekall.rekallJsonDirectiveTest');

const {rekallModule} = goog.require('grrUi.semantic.rekall.rekall');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('Rekall JSON directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module(
      '/static/angular-components/semantic/rekall/rekall-json.html'));
  beforeEach(module(rekallModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrRekallLog');
  stubDirective('grrRekallMetadata');
  stubDirective('grrRekallTable');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (jsonContextMessages, compressedJsonMessages) => {
    $rootScope.jsonContextMessages = {'value': jsonContextMessages};
    $rootScope.compressedJsonMessages = {'value': compressedJsonMessages};

    const template = '<grr-rekall-json ' +
        '    json-context-messages="jsonContextMessages" ' +
        '    compressed-json-messages="compressedJsonMessages">' +
        '</grr-rekall-json>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing when the input is empty', () => {
    const element = renderTestTemplate('[]', '[]');

    expect(element.find('div').length).toBe(0);
  });

  it('shows messages of known types.', () => {
    const element =
        renderTestTemplate('[["t", {}]]', '[["L", {}], ["m", {}], ["r", {}]]');

    expect(element.find('div').length).toBe(3);
    expect(element.find('grr-rekall-log').length).toBe(1);
    expect(element.find('grr-rekall-metadata').length).toBe(1);
    expect(element.find('grr-rekall-table').length).toBe(1);
  });

  it('shows EOM for messages of type "x".', () => {
    const element = renderTestTemplate('[]', '[["x", {}]]');

    expect(element.find('div').length).toBe(1);
    expect(element.text()).toContain('EOM');
  });

  it('shows its input for messages of unknown type.', () => {
    const element = renderTestTemplate('[]', '[["?", {}]]');

    expect(element.find('div').length).toBe(1);
    expect(element.text()).toContain('["?",{}]');
  });
});


exports = {};
