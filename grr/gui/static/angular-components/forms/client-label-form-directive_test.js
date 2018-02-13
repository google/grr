'use strict';

goog.module('grrUi.forms.clientLabelFormDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {formsModule} = goog.require('grrUi.forms.forms');


describe('client label form directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;

  const defaultOption = '-- All clients --';

  beforeEach(module('/static/angular-components/forms/client-label-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');

    spyOn(grrApiService, 'get').and.callFake((url) => {
      const deferred = $q.defer();

      if (url === '/clients/labels') {
        deferred.resolve({
          data: {
            items: [
              {
                type: 'AFF4ObjectLabel',
                value: {
                  name: {
                    type: 'unicode',
                    value: 'ClientLabelFoo',
                  },
                },
              },
              {
                type: 'AFF4ObjectLabel',
                value: {
                  name: {
                    type: 'unicode',
                    value: 'ClientLabelBar',
                  },
                },
              },
            ],
          },
        });
      } else {
        throw new Error(`Unexpected url: ${url}`);
      }

      return deferred.promise;
    });
  }));

  const renderTestTemplate =
      ((clientLabel, formLabel, hideEmptyOption, emptyOptionLabel) => {
        $rootScope.clientLabel = clientLabel;
        $rootScope.formLabel = formLabel;
        $rootScope.hideEmptyOption = hideEmptyOption;
        $rootScope.emptyOptionLabel = emptyOptionLabel;

        const template = '<grr-form-client-label ' +
            'client-label="clientLabel" ' +
            'form-label="formLabel" ' +
            'hide-empty-option="hideEmptyOption" ' +
            'empty-option-label="emptyOptionLabel" ' +
            '></grr-form-client-label>';
        const element = $compile(template)($rootScope);
        $rootScope.$apply();

        return element;
      });

  it('shows the list of available client labels', () => {
    const element = renderTestTemplate('');

    const select = element.find('select');
    const children = select.children();
    const options = children.map((index) => children[index].innerText);

    expect(options).toContain(defaultOption);
    expect(options).toContain('ClientLabelFoo');
    expect(options).toContain('ClientLabelBar');
  });

  it('selects the label given through scope params initially', () => {
    const initialSelection = 'ClientLabelFoo';
    const element = renderTestTemplate(initialSelection);

    const select = element.find('select');
    const children = select.children();

    let found = false;
    for (let i = 0; i < children.length; ++i) {
      expect(children[i].selected).toBe(
          children[i].innerText === initialSelection);

      if (children[i].selected) {
        found = true;
      }
    }

    // Ensure the selected element exists in children.
    expect(found).toBe(true);
  });

  it('shows default <label> text by default', () => {
    const element = renderTestTemplate('');

    const labelTag = element.find('label');

    expect(labelTag.text()).toBe('Client label');
  });

  it('shows custom <label> text if given', () => {
    const element = renderTestTemplate('', 'Custom label text');

    const labelTag = element.find('label');

    expect(labelTag.text()).toBe('Custom label text');
  });

  it('forwards value changes to parent scope', () => {
    const element = renderTestTemplate('');

    const select = element.find('select');
    const newSelection = 'ClientLabelBar';
    select.val(`string:${newSelection}`);

    browserTriggerEvent(select, 'change');
    $rootScope.$apply();

    expect(element.scope().$eval(element.attr('client-label'))).toEqual(
        newSelection);
  });

  it('hides the empty option if requested', () => {
    const element =
        renderTestTemplate('', undefined, /* hideEmptyOption */ true);

    const select = element.find('select');
    const children = select.children();
    const options = children.map((index) => children[index].innerText);

    expect(options).not.toContain(defaultOption);
  });

  it('displays a given string describing the empty option if requested', () => {
    const customDefaultOption = 'Custom empty option description';
    const element = renderTestTemplate(
        '', undefined, undefined, /* emptyOptionLabel */ customDefaultOption);

    const select = element.find('select');
    const children = select.children();
    const options = children.map((index) => children[index].innerText);

    expect(options).not.toContain(defaultOption);
    expect(options).toContain(customDefaultOption);
  });
});


exports = {};
