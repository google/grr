'use strict';

goog.module('grrUi.forms.bytesFormDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {bytesToHexEncodedString, hexEncodedStringToBytes, isByteString} = goog.require('grrUi.forms.bytesFormDirective');
const {formsModule} = goog.require('grrUi.forms.forms');


const hexChars = String.fromCharCode(13) + String.fromCharCode(200);
const encodedHexChars = '\\x0d\\xc8';
const nonHexChars = 'foo';

describe('bytesToHexEncodedString()', () => {
  it('does nothing with an empty string', () => {
    expect(bytesToHexEncodedString('')).toBe('');
  });

  it('doesn\'t encode characters with codes from 32 to 126', () => {
    let s = '';
    for (let i = 32; i <= 126; ++i) {
      s += String.fromCharCode(i);
    }

    expect(bytesToHexEncodedString(s)).toBe(s);
  });

  it('encodes characters with codes from 0 to 31 and from 127 to 255', () => {
    for (let i = 0; i <= 31; ++i) {
      const s = String.fromCharCode(i);
      expect(bytesToHexEncodedString(s)).toMatch(/\\x[0-9A-Fa-f]{2}/);
    }
  });


  it('encodes hex chars in the beginning of the string', () => {
    expect(bytesToHexEncodedString(hexChars + nonHexChars))
        .toBe(encodedHexChars + nonHexChars);
  });

  it('encodes hex chars in the middle of the string', () => {
    expect(bytesToHexEncodedString(nonHexChars + hexChars + nonHexChars))
        .toBe(nonHexChars + encodedHexChars + nonHexChars);
  });

  it('encodes hex chars in the end of the string', () => {
    expect(bytesToHexEncodedString(nonHexChars + hexChars))
        .toBe(nonHexChars + encodedHexChars);
  });

  it('encodes hex chars in the beginning and end of the string', () => {
    expect(bytesToHexEncodedString(hexChars + nonHexChars + hexChars))
        .toBe(encodedHexChars + nonHexChars + encodedHexChars);
  });
});

describe('hexEncodedStringToBytes()', () => {
  it('does nothing with an empty string', () => {
    expect(hexEncodedStringToBytes('')).toBe('');
  });

  it('decodes all possible characters', () => {
    for (let i = 0; i < 256; ++i) {
      let s = i.toString(16);
      if (s.length == 1) {
        s = `0${s}`;
      }
      s = `\\x${s}`;

      expect(hexEncodedStringToBytes(s)).toBe(String.fromCharCode(i));
    }
  });

  it('decodes hex chars in the beginning of the string', () => {
    expect(hexEncodedStringToBytes(encodedHexChars + nonHexChars))
        .toBe(hexChars + nonHexChars);
  });

  it('decodes hex chars in the middle of the string', () => {
    expect(hexEncodedStringToBytes(nonHexChars + encodedHexChars + nonHexChars))
        .toBe(nonHexChars + hexChars + nonHexChars);
  });

  it('decodes hex chars in the end of the string', () => {
    expect(hexEncodedStringToBytes(nonHexChars + encodedHexChars))
        .toBe(nonHexChars + hexChars);
  });

  it('decodes hex chars in the beginning and end of the string', () => {
    expect(hexEncodedStringToBytes(
        encodedHexChars + nonHexChars + encodedHexChars))
            .toBe(hexChars + nonHexChars + hexChars);
  });
});

describe('isByteString()', () => {
  it('returns true if a string had only characters with car code < 256', () => {
    let s = '';
    for (let i = 0; i < 256; ++i) {
      s += String.fromCharCode(i);
    }

    expect(isByteString(s)).toBe(true);
  });

  it('returns false if a string has a character with a char code >= 256',
     () => {
       expect(isByteString(String.fromCharCode(256))).toBe(false);
     });
});

describe('bytes form directive', () => {
  let $compile;
  let $rootScope;

  beforeEach(module('/static/angular-components/forms/bytes-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-form-bytes value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing if value is null', () => {
    const element = renderTestTemplate({
      type: 'RDFBytes',
      value: null,
    });
    expect(element.find('input').val()).toBe('');
  });

  it('shows base64-decoded value for plain latin characters', () => {
    const element = renderTestTemplate({
      type: 'RDFBytes',
      value: window.btoa('foo'),
    });
    expect(element.find('input').val()).toBe('foo');
  });

  it('shows nothing for incorrectly base64-encoded value', () => {
    const element = renderTestTemplate({
      type: 'RDFBytes',
      value: '--',
    });
    expect(element.find('input').val()).toBe('');
  });

  it('updates value to a base64 version on input', () => {
    const value = {
      type: 'RDFBytes',
      value: '',
    };
    const element = renderTestTemplate(value);

    element.find('input').val('a');
    browserTriggerEvent(element.find('input'), 'change');
    expect(value.value).toBe('YQ==');
  });

  it('updates value coorectly on hex-encoded input', () => {
    const value = {
      type: 'RDFBytes',
      value: '',
    };
    const element = renderTestTemplate(value);

    // Simulate user gradually typing \\x0d
    element.find('input').val('\\');
    browserTriggerEvent(element.find('input'), 'change');
    expect(value.value).toBe('XA==');

    element.find('input').val('\\x');
    browserTriggerEvent(element.find('input'), 'change');
    expect(value.value).toBe('XHg=');

    element.find('input').val('\\x0');
    browserTriggerEvent(element.find('input'), 'change');
    expect(value.value).toBe('XHgw');

    element.find('input').val('\\x0d');
    browserTriggerEvent(element.find('input'), 'change');
    expect(value.value).toBe('DQ==');
  });

  it('shows a validation message on unicode input', () => {
    const value = {
      type: 'RDFBytes',
      value: '',
    };
    const element = renderTestTemplate(value);
    element.find('input').val('昨');
    browserTriggerEvent(element.find('input'), 'change');

    expect(element.text()).toContain(
        'Unicode characters are not allowed in a byte string');
  });

  it('updates value.validationError on unicode input', () => {
    const value = {
      type: 'RDFBytes',
      value: '',
    };
    const element = renderTestTemplate(value);
    element.find('input').val('昨');
    browserTriggerEvent(element.find('input'), 'change');

    expect(value.validationError).toContain(
        'Unicode characters are not allowed in a byte string');
  });
});


exports = {};
