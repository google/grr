'use strict';

goog.module('grrUi.forms.extFlagsLinuxPickerLongDirectiveTest');

const {ExtFlagsLinuxPickerLongDirective} = goog.require('grrUi.forms.extFlagsLinuxPickerLongDirective');
const {LINUX_FLAGS, getLinuxFlagMaskByNames} = goog.require('grrUi.client.extFlags');
const {formsModule} = goog.require('grrUi.forms.forms');
const {testsModule} = goog.require('grrUi.tests');


describe('Extended flags picker for Linux (long)', () => {
  let $compile;
  let $rootScope;

  beforeEach(module(ExtFlagsLinuxPickerLongDirective().templateUrl));

  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const render = (bits) => {
    $rootScope.bitsSet = bits.set;
    $rootScope.bitsUnset = bits.unset;

    const template = `<grr-ext-flags-linux-picker-long
      bits-set="bitsSet"
      bits-unset="bitsUnset" />`;

    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  const parse = (element) => {
    const result = {};
    for (const flag of LINUX_FLAGS) {
      const option = $(element.find(`#${flag.name}`)).find('option[selected]');
      result[flag.name] = option.text();
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
      expect(table[flag.name]).toBe('ignored');
    }
  });

  it('correctly renders a table if some bits are set', () => {
    const table = parse(render({
      set: {
        value: getLinuxFlagMaskByNames(['FS_SYNC_FL', 'FS_UNRM_FL']),
      },
      unset: {
        value: 0,
      },
    }));

    expect(table['FS_SYNC_FL']).toBe('required set');
    expect(table['FS_UNRM_FL']).toBe('required set');
    expect(table['FS_IMMUTABLE_FL']).toBe('ignored');
  });

  it('correctly renders a table if some bits are unset', () => {
    const table = parse(render({
      set: {
        value: 0,
      },
      unset: {
        value: getLinuxFlagMaskByNames(['FS_IMMUTABLE_FL', 'FS_COMPR_FL']),
      },
    }));

    expect(table['FS_IMMUTABLE_FL']).toBe('required unset');
    expect(table['FS_COMPR_FL']).toBe('required unset');
    expect(table['FS_SYNC_FL']).toBe('ignored');
  });

  it('correctly renders a table if there are bits set and bits unset', () => {
    const table = parse(render({
      set: {
        value: getLinuxFlagMaskByNames(['FS_NOATIME_FL']),
      },
      unset: {
        value: getLinuxFlagMaskByNames(['FS_DIRTY_FL', 'FS_INDEX_FL']),
      },
    }));

    expect(table['FS_NOATIME_FL']).toBe('required set');
    expect(table['FS_DIRTY_FL']).toBe('required unset');
    expect(table['FS_INDEX_FL']).toBe('required unset');
    expect(table['FS_TOPDIR_FL']).toBe('ignored');
  });
});
