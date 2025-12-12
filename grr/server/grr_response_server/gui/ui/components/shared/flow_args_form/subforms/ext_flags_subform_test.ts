import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {FormGroup, ReactiveFormsModule} from '@angular/forms';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FileFinderExtFlagsCondition} from '../../../../lib/api/api_interfaces';
import {OperatingSystem} from '../../../../lib/models/flow';
import {
  getLinuxFlagByName,
  getOsxFlagByName,
  getOsxFlagMaskByNames,
} from '../../../../lib/models/os_extended_flags';
import {initTestEnvironment} from '../../../../testing';
import {ExtFlagsSubform, createExtFlagsFormGroup} from './ext_flags_subform';
import {ExtFlagsSubformHarness} from './testing/ext_flags_subform_harness';

initTestEnvironment();

@Component({
  selector: 'ext-flags-condition-test',
  template: `
    <form [formGroup]="formGroup">
      <ext-flags-subform [formGroup]="formGroup.controls.extFlags" [clientOs]="clientOs()"/>
    </form>
  `,
  imports: [CommonModule, ExtFlagsSubform, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
class TestComponent {
  readonly formGroup = new FormGroup({
    extFlags: createExtFlagsFormGroup(),
  });
  readonly clientOs = input.required<OperatingSystem | undefined>();
}

async function createComponent(os: OperatingSystem | undefined) {
  const fixture = TestBed.createComponent(TestComponent);
  fixture.componentRef.setInput('clientOs', os);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ExtFlagsSubformHarness,
  );
  return {fixture, harness};
}

describe('ExtFlagsCondition component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ExtFlagsSubform],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('sets bits when clicking once on flag', async () => {
    const {harness, fixture} = await createComponent(OperatingSystem.DARWIN);
    await harness.selectIncludeFlag('nodump');

    const expected: FileFinderExtFlagsCondition = {
      linuxBitsSet: 0,
      linuxBitsUnset: 0,
      osxBitsSet: getOsxFlagMaskByNames(['UF_NODUMP']),
      osxBitsUnset: 0,
    };

    expect(fixture.componentInstance.formGroup.controls.extFlags.value).toEqual(
      expected,
    );
  });

  it('unsets bits when reverting selection', async () => {
    const {harness, fixture} = await createComponent(OperatingSystem.DARWIN);
    await harness.selectIncludeFlag('nodump');
    await harness.selectEitherFlag('nodump');

    const expected: FileFinderExtFlagsCondition = {
      linuxBitsSet: 0,
      linuxBitsUnset: 0,
      osxBitsSet: 0,
      osxBitsUnset: 0,
    };

    expect(fixture.componentInstance.formGroup.controls.extFlags.value).toEqual(
      expected,
    );
  });

  it('computes logical OR of all checked flags', async () => {
    const {harness, fixture} = await createComponent(OperatingSystem.DARWIN);
    await harness.selectIncludeFlag('nodump');
    await harness.selectIncludeFlag('opaque');

    const expected: FileFinderExtFlagsCondition = {
      linuxBitsSet: 0,
      linuxBitsUnset: 0,
      osxBitsSet:
        getOsxFlagByName('UF_NODUMP').mask | getOsxFlagByName('UF_OPAQUE').mask,
      osxBitsUnset: 0,
    };

    expect(fixture.componentInstance.formGroup.controls.extFlags.value).toEqual(
      expected,
    );
  });

  it('sets set and unset flags', async () => {
    const {harness, fixture} = await createComponent(OperatingSystem.DARWIN);
    await harness.selectIncludeFlag('nodump');
    await harness.selectExcludeFlag('opaque');

    const expected: FileFinderExtFlagsCondition = {
      linuxBitsSet: 0,
      linuxBitsUnset: 0,
      osxBitsSet: getOsxFlagByName('UF_NODUMP').mask,
      osxBitsUnset: getOsxFlagByName('UF_OPAQUE').mask,
    };

    expect(fixture.componentInstance.formGroup.controls.extFlags.value).toEqual(
      expected,
    );
  });

  it('can set linux and osx flags', async () => {
    const {harness, fixture} = await createComponent(OperatingSystem.WINDOWS);

    await harness.selectIncludeFlag('T');
    await harness.selectExcludeFlag('nodump');

    const expected: FileFinderExtFlagsCondition = {
      linuxBitsSet: getLinuxFlagByName('FS_TOPDIR_FL').mask,
      linuxBitsUnset: 0,
      osxBitsSet: 0,
      osxBitsUnset: getOsxFlagByName('UF_NODUMP').mask,
    };

    expect(fixture.componentInstance.formGroup.controls.extFlags.value).toEqual(
      expected,
    );
  });

  it('shows only macOS flags (not linux) if client is macOS', async () => {
    const {harness} = await createComponent(OperatingSystem.DARWIN);

    expect(await harness.hasFlag('nodump')).toBeTrue();
    expect(await harness.hasFlag('T')).toBeFalse();
  });

  it('shows only linux flags (not macOS) if client is linux', async () => {
    const {harness} = await createComponent(OperatingSystem.LINUX);

    expect(await harness.hasFlag('nodump')).toBeFalse();
    expect(await harness.hasFlag('T')).toBeTrue();
  });

  it('shows both linux and macOS flags for other clients', async () => {
    const {harness} = await createComponent(OperatingSystem.WINDOWS);

    expect(await harness.hasFlag('nodump')).toBeTrue();
    expect(await harness.hasFlag('T')).toBeTrue();
  });

  it('shows both linux and macOS flags for unknown clients', async () => {
    const {harness} = await createComponent(undefined);

    expect(await harness.hasFlag('nodump')).toBeTrue();
    expect(await harness.hasFlag('T')).toBeTrue();
  });
});
