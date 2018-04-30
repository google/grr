'use strict';

goog.module('grrUi.forms.extFlagsOsxPickerDirectiveTest');

const {ExtFlagsOsxPickerDirective} = goog.require('grrUi.forms.extFlagsOsxPickerDirective');
const {OSX_FLAGS, getOsxFlagMaskByNames} = goog.require('grrUi.client.extFlags');
const {TroggleDirective} = goog.require('grrUi.core.troggleDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {formsModule} = goog.require('grrUi.forms.forms');
const {testsModule} = goog.require('grrUi.tests');


describe('Extended flags picker for macOS', () => {
  let $compile;
  let $rootScope;

  beforeEach(module(TroggleDirective().templateUrl));
  beforeEach(module(ExtFlagsOsxPickerDirective().templateUrl));

  beforeEach(module(coreModule.name));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const render = (bits) => {
    $rootScope.bitsSet = bits.set;
    $rootScope.bitsUnset = bits.unset;

    const template = `<grr-ext-flags-osx-picker
      bits-set="bitsSet"
      bits-unset="bitsUnset" />`;

    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  const parse = (element) => {
    const ths = element.find('th');
    const tds = element.find('td');
    expect(ths.length).toBe(tds.length);

    const result = {};
    for (let i = 0; i < ths.length; i++) {
      result[$(ths[i]).text().trim()] = $(tds[i]).text().trim();
    }
    return result;
  };

  it('correctly renders a table if set and unset bits are empty', () => {
    const table = parse(render({
      set: {
        value: 0,
      },
      unset: {
        value: 0,
      },
    }));

    for (const flag of OSX_FLAGS) {
      expect(table[flag.identifier]).toBe('_');
    }
  });

  it('correctly renders a table if some bits are set', () => {
    const table = parse(render({
      set: {
        value: getOsxFlagMaskByNames(['UF_NODUMP', 'UF_IMMUTABLE']),
      },
      unset: {
        value: 0,
      },
    }));

    expect(table['nodump']).toBe('✓');
    expect(table['uimmutable']).toBe('✓');
    expect(table['archived']).toBe('_');
  });

  it('correctly renders a table if some bits are unset', () => {
    const table = parse(render({
      set: {
        value: 0,
      },
      unset: {
        value: getOsxFlagMaskByNames(['SF_APPEND', 'SF_NOUNLINK']),
      },
    }));

    expect(table['sappend']).toBe('✕');
    expect(table['sunlnk']).toBe('✕');
    expect(table['opaque']).toBe('_');
  });

  it('correctly renders a table if there are bits set and bits unset', () => {
    const table = parse(render({
      set: {
        value: getOsxFlagMaskByNames(['UF_APPEND']),
      },
      unset: {
        value: getOsxFlagMaskByNames(['SF_APPEND']),
      },
    }));

    expect(table['uappend']).toBe('✓');
    expect(table['sappend']).toBe('✕');
    expect(table['uimmutable']).toBe('_');
    expect(table['simmutable']).toBe('_');
  });
});
