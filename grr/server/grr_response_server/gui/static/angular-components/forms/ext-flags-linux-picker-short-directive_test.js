'use strict';

goog.module('grrUi.forms.extFlagsLinuxPickerShortDirectiveTest');

const {ExtFlagsLinuxPickerShortDirective} = goog.require('grrUi.forms.extFlagsLinuxPickerShortDirective');
const {LINUX_FLAGS, getLinuxFlagMaskByNames} = goog.require('grrUi.client.extFlags');
const {TroggleDirective} = goog.require('grrUi.core.troggleDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {formsModule} = goog.require('grrUi.forms.forms');
const {testsModule} = goog.require('grrUi.tests');


describe('Extended flags picker for Linux (short)', () => {
  let $compile;
  let $rootScope;

  beforeEach(module(TroggleDirective().templateUrl));
  beforeEach(module(ExtFlagsLinuxPickerShortDirective().templateUrl));

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

    const template = `<grr-ext-flags-linux-picker-short
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

    for (const flag of LINUX_FLAGS) {
      expect(table[flag.identifier]).toBe('_');
    }
  });

  it('correctly renders a table if some bits are set', () => {
    const table = parse(render({
      set: {
        value: getLinuxFlagMaskByNames(['FS_IMMUTABLE_FL', 'FS_APPEND_FL']),
      },
      unset: {
        value: 0,
      },
    }));

    expect(table['a']).toBe('✓');
    expect(table['i']).toBe('✓');
    expect(table['c']).toBe('_');
    expect(table['s']).toBe('_');
  });

  it('correctly renders a table if some bits are unset', () => {
    const table = parse(render({
      set: {
        value: 0,
      },
      unset: {
        value: getLinuxFlagMaskByNames(['FS_NOCOMP_FL', 'FS_NODUMP_FL']),
      },
    }));

    expect(table['X']).toBe('✕');
    expect(table['d']).toBe('✕');
    expect(table['a']).toBe('_');
    expect(table['B']).toBe('_');
  });

  it('correctly renders a table if there are bits set and bits unset', () => {
    const table = parse(render({
      set: {
        value: getLinuxFlagMaskByNames(['FS_EXTENT_FL']),
      },
      unset: {
        value: getLinuxFlagMaskByNames(['FS_TOPDIR_FL', 'FS_NOCOW_FL']),
      },
    }));

    expect(table['e']).toBe('✓');
    expect(table['T']).toBe('✕');
    expect(table['C']).toBe('✕');
    expect(table['a']).toBe('_');
  });
});
