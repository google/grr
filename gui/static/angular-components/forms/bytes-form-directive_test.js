'use strict';

goog.require('grrUi.forms.bytesFormDirective.bytesToHexEncodedString');
goog.require('grrUi.forms.bytesFormDirective.hexEncodedStringToBytes');

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');


var browserTrigger = grrUi.tests.browserTrigger;

var hexChars = String.fromCharCode(13) + String.fromCharCode(200);
var encodedHexChars = '\\x0d\\xc8';
var nonHexChars = 'foo';

describe('bytesToHexEncodedString()', function() {
  var bytesToHexEncodedString =
      grrUi.forms.bytesFormDirective.bytesToHexEncodedString;

  it('does nothing with an empty string', function() {
    expect(bytesToHexEncodedString('')).toBe('');
  });

  it('doesn\'t encode characters with codes from 32 to 126', function() {
    var s = '';
    for (var i = 32; i <= 126; ++i) {
      s += String.fromCharCode(i);
    }

    expect(bytesToHexEncodedString(s)).toBe(s);
  });

  it('encodes characters with codes from 0 to 31 and from 127 to 255',
     function() {
    var i, s;
    for (i = 0; i <= 31; ++i) {
      s = String.fromCharCode(i);
      expect(bytesToHexEncodedString(s)).toMatch(/\\x[0-9A-Fa-f]{2}/);
    }
  });


  it('encodes hex chars in the beginning of the string', function() {
    expect(bytesToHexEncodedString(hexChars + nonHexChars))
        .toBe(encodedHexChars + nonHexChars);
  });

  it('encodes hex chars in the middle of the string', function() {
    expect(bytesToHexEncodedString(nonHexChars + hexChars + nonHexChars))
        .toBe(nonHexChars + encodedHexChars + nonHexChars);
  });

  it('encodes hex chars in the end of the string', function() {
    expect(bytesToHexEncodedString(nonHexChars + hexChars))
        .toBe(nonHexChars + encodedHexChars);
  });

  it('encodes hex chars in the beginning and end of the string', function() {
    expect(bytesToHexEncodedString(hexChars + nonHexChars + hexChars))
        .toBe(encodedHexChars + nonHexChars + encodedHexChars);
  });
});

describe('hexEncodedStringToBytes()', function() {
  var hexEncodedStringToBytes =
      grrUi.forms.bytesFormDirective.hexEncodedStringToBytes;

  it('does nothing with an empty string', function() {
    expect(hexEncodedStringToBytes('')).toBe('');
  });

  it('decodes all possible characters', function() {
    for (var i = 0; i < 256; ++i) {
      var s = i.toString(16);
      if (s.length == 1) {
        s = '0' + s;
      }
      s = '\\x' + s;

      expect(hexEncodedStringToBytes(s)).toBe(String.fromCharCode(i));
    }
  });

  it('decodes hex chars in the beginning of the string', function() {
    expect(hexEncodedStringToBytes(encodedHexChars + nonHexChars))
        .toBe(hexChars + nonHexChars);
  });

  it('decodes hex chars in the middle of the string', function() {
    expect(hexEncodedStringToBytes(nonHexChars + encodedHexChars + nonHexChars))
        .toBe(nonHexChars + hexChars + nonHexChars);
  });

  it('decodes hex chars in the end of the string', function() {
    expect(hexEncodedStringToBytes(nonHexChars + encodedHexChars))
        .toBe(nonHexChars + hexChars);
  });

  it('decodes hex chars in the beginning and end of the string', function() {
    expect(hexEncodedStringToBytes(
        encodedHexChars + nonHexChars + encodedHexChars))
            .toBe(hexChars + nonHexChars + hexChars);
  });
});

describe('bytes form directive', function() {
  var $compile, $rootScope, value;

  beforeEach(module('/static/angular-components/forms/bytes-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-form-bytes value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing if value is null', function() {
    var element = renderTestTemplate({
      type: 'RDFBytes',
      value: null
    });
    expect(element.find('input').val()).toBe('');
  });

  it('shows base64-decoded value for plain latin characters', function() {
    var element = renderTestTemplate({
      type: 'RDFBytes',
      value: window.btoa('foo')
    });
    expect(element.find('input').val()).toBe('foo');
  });

  it('shows nothing for incorrectly base64-encoded value', function() {
    var element = renderTestTemplate({
      type: 'RDFBytes',
      value: '--'
    });
    expect(element.find('input').val()).toBe('');
  });

  it('updates value to a base64 version on input', function() {
    var value = {
      type: 'RDFBytes',
      value: ''
    };
    var element = renderTestTemplate(value);

    element.find('input').val('a');
    browserTrigger(element.find('input'), 'change');
    expect(value.value).toBe('YQ==');
  });

  it('updates value coorectly on hex-encoded input', function() {
    var value = {
      type: 'RDFBytes',
      value: ''
    };
    var element = renderTestTemplate(value);

    // Simulate user gradually typing \\x0d
    element.find('input').val('\\');
    browserTrigger(element.find('input'), 'change');
    expect(value.value).toBe('XA==');

    element.find('input').val('\\x');
    browserTrigger(element.find('input'), 'change');
    expect(value.value).toBe('XHg=');

    element.find('input').val('\\x0');
    browserTrigger(element.find('input'), 'change');
    expect(value.value).toBe('XHgw');

    element.find('input').val('\\x0d');
    browserTrigger(element.find('input'), 'change');
    expect(value.value).toBe('DQ==');
  });
});
