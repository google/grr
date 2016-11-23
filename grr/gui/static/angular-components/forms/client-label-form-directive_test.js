'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.module');


describe('client label form directive', function() {
  var $compile, $rootScope, value, $q, grrApiService;
  var defaultOption = '-- All clients --';

  beforeEach(module('/static/angular-components/forms/client-label-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');

    spyOn(grrApiService, 'get').and.callFake(function(url) {
          var deferred = $q.defer();

          if (url === '/clients/labels') {
            deferred.resolve({
              data: {
                items: [
                  {
                    type: 'AFF4ObjectLabel',
                    value: {
                      name: {
                        type: 'unicode',
                        value: 'ClientLabelFoo'
                      }
                    }
                  },
                  {
                    type: 'AFF4ObjectLabel',
                    value: {
                      name: {
                        type: 'unicode',
                        value: 'ClientLabelBar'
                      }
                    }
                  }
                ]
              }
            });
          } else {
            throw new Error('Unexpected url: ' + url);
          }

          return deferred.promise;
        });
  }));

  var renderTestTemplate = function(clientLabel, formLabel) {
    $rootScope.clientLabel = clientLabel;

    if (angular.isDefined(formLabel)) {
      $rootScope.formLabel = formLabel;
    }

    var template = '<grr-form-client-label ' +
                       'client-label="clientLabel" ' +

                       (angular.isDefined(formLabel) ?
                       'form-label="formLabel" ' : '') +
                   '></grr-form-client-label>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows the list of available client labels', function() {
    var element = renderTestTemplate('');

    var select = element.find('select');
    var children = select.children();
    var options = children.map(function(index) {
        return children[index].innerText;
    });

    expect(options).toContain(defaultOption);
    expect(options).toContain('ClientLabelFoo');
    expect(options).toContain('ClientLabelBar');
  });

  it('selects the label given through scope params initially', function() {
    var initialSelection = 'ClientLabelFoo';
    var element = renderTestTemplate(initialSelection);

    var select = element.find('select');
    var children = select.children();

    var found = false;
    for (var i = 0; i < children.length; ++i) {
      expect(children[i].selected).toBe(
          children[i].innerText === initialSelection);

      if (children[i].selected) {
        found = true;
      }
    }

    // Ensure the selected element exists in children.
    expect(found).toBe(true);
  });

  it('shows default <label> text by default', function() {
    var element = renderTestTemplate('');

    var labelTag = element.find('label');

    expect(labelTag.text()).toBe('Client label');
  });

  it('shows custom <label> text if given', function() {
    var element = renderTestTemplate('', 'Custom label text');

    var labelTag = element.find('label');

    expect(labelTag.text()).toBe('Custom label text');
  });

  it('forwards value changes to parent scope', function() {
    var element = renderTestTemplate('');

    var select = element.find('select');
    var newSelection = 'ClientLabelBar';
    select.val('string:' + newSelection);

    browserTrigger(select, 'change');
    $rootScope.$apply();

    expect(element.scope().$eval(element.attr('client-label'))).toEqual(
        newSelection);
  });

});
