goog.module('grrUi.user.approverInputDirectiveTest');
goog.setTestOnly();

const {testsModule} = goog.require('grrUi.tests');
const {userModule} = goog.require('grrUi.user.user');


describe('approver input', () => {
  let $compile;
  let $rootScope;
  let grrApiService;

  beforeEach(module('/static/angular-components/user/approver-input.html'));
  beforeEach(module('/static/angular-components/core/typeahead-match.html'));
  beforeEach(module(userModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    const $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');

    const approverSuggestions = [
      {
        value: {username: {value: 'sanchezmorty', type: 'unicode'}},
        type: 'ApproverSuggestion',
      },
      {
        value: {username: {value: 'sanchezrick', type: 'unicode'}},
        type: 'ApproverSuggestion',
      },
      {
        value: {username: {value: 'sanchezsummer', type: 'unicode'}},
        type: 'ApproverSuggestion',
      },
    ];

    spyOn(grrApiService, 'get').and.callFake((url, params) => {
      const deferred = $q.defer();
      const suggestions = approverSuggestions.filter(
          sugg => sugg.value.username.value.startsWith(params.username_query));
      deferred.resolve({data: {suggestions}});
      return deferred.promise;
    });
  }));

  function renderTestTemplate(initialValue = '') {
    const template = '<grr-approver-input ng-model="value"/>';
    $rootScope.value = initialValue;

    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  }

  function type(element, text) {
    $('input', element).val(text).trigger('input').trigger('change');
  }

  it('renders a text input', () => {
    const element = renderTestTemplate();
    expect($('input', element).length).toBe(1);
  });

  it('calls API for username input', () => {
    const element = renderTestTemplate();
    type(element, 'sanchezsu');

    expect(grrApiService.get)
        .toHaveBeenCalledWith('/users/approver-suggestions', {
          username_query: 'sanchezsu',
        });
  });

  it('calls API for rightmost username', () => {
    const element = renderTestTemplate();

    type(element, 'foo,bar');
    expect(grrApiService.get)
        .toHaveBeenCalledWith('/users/approver-suggestions', {
          username_query: 'bar',
        });

    type(element, 'bar,foo');
    expect(grrApiService.get)
        .toHaveBeenCalledWith('/users/approver-suggestions', {
          username_query: 'foo',
        });

    type(element, 'foo , bar , baz');
    expect(grrApiService.get)
        .toHaveBeenCalledWith('/users/approver-suggestions', {
          username_query: 'baz',
        });
  });

  it('shows autocomplete for single suggestion', () => {
    const element = renderTestTemplate();
    type(element, 'sanchezsu');

    expect($('[uib-typeahead-popup] li').length).toBe(1);
    expect($('[uib-typeahead-popup] li:eq(0)').text().trim())
        .toBe('sanchezsummer');
  });

  it('shows autocomplete for multiple suggestions', () => {
    const element = renderTestTemplate();
    type(element, 'san');

    expect($('[uib-typeahead-popup] li').length).toBe(3);
    expect($('[uib-typeahead-popup] li:eq(0)').text().trim())
        .toBe('sanchezmorty');
    expect($('[uib-typeahead-popup] li:eq(1)').text().trim())
        .toBe('sanchezrick');
    expect($('[uib-typeahead-popup] li:eq(2)').text().trim())
        .toBe('sanchezsummer');
  });

  it('does not show previous usernames in autocomplete', () => {
    const element = renderTestTemplate();
    type(element, 'sanchezsummer, san');

    expect($('[uib-typeahead-popup] li').length).toBe(2);
    expect($('[uib-typeahead-popup] li:eq(0)').text().trim())
        .toBe('sanchezmorty');
    expect($('[uib-typeahead-popup] li:eq(1)').text().trim())
        .toBe('sanchezrick');
  });

  it('does not show autocomplete for empty input', () => {
    const element = renderTestTemplate();
    type(element, '');

    expect(grrApiService.get).not.toHaveBeenCalled();
    expect($('[uib-typeahead-popup] li').length).toBe(0);
  });

  it('does not show autocomplete for empty search', () => {
    const element = renderTestTemplate();
    type(element, 'sanchez, ');

    expect(grrApiService.get).not.toHaveBeenCalled();
    expect($('[uib-typeahead-popup] li').length).toBe(0);
  });

  it('uses value from ng-model', () => {
    const element = renderTestTemplate('foo');
    expect($('input', element).val()).toBe('foo');
  });

  it('correctly assigns ng-model', () => {
    const element = renderTestTemplate();
    type(element, 'sanchez, foo, ');
    expect(element.scope().value).toBe('sanchez, foo, ');
  });
});


exports = {};
