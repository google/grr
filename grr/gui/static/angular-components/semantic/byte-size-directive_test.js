'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('grrByteSize directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/semantic/byte-size.html'));
  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-byte-size value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows "-" when value is empty', function() {
    var value = {
      type: 'ByteSize',
      value: null
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('-');
  });

  it('shows 0 if value is 0', function() {
    var value = {
      type: 'ByteSize',
      value: 0
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('0');
  });

  it('shows value in bytes if it is less than 1024', function() {
    var value = {
      type: 'ByteSize',
      value: 42,
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('42b');
  });

  it('shows value in kilobytes if it is less than 1024**2', function() {
    var value = {
      type: 'ByteSize',
      value: 1124
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('1.1Kb');
  });

  it('shows value in megabytes if it is less than 1024**3', function() {
    var value = {
      type: 'ByteSize',
      value: 44040192
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('42Mb');
  });

  it('shows value in gigabytes if it is more than 1024**3', function() {
    var value = {
      type: 'ByteSize',
      value: 1610612736
    };
    var element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('1.5Gb');
  });

  it('shows value in bytes in the tooltip', function() {
    var value = {
      type: 'ByteSize',
      value: 1610612736
    };
    var element = renderTestTemplate(value);
    expect(element.find('span').attr('title')).toBe('1610612736 bytes');
  });
});
