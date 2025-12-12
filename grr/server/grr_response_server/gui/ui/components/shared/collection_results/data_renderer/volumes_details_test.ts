import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';

import {initTestEnvironment} from '../../../../testing';
import {VolumesDetailsHarness} from './testing/volumes_details_harness';
import {VolumesDetails} from './volumes_details';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(VolumesDetails);
  // Set the default value here as the input is required.
  fixture.componentRef.setInput('volumes', []);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    VolumesDetailsHarness,
  );
  return {fixture, harness};
}

describe('Volumes Details Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [VolumesDetails],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('shows `None` if there are no volumes', async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput('volumes', []);
    expect(await harness.hasNoneText()).toBeTrue();
    expect(await harness.numTables()).toBe(0);
  });

  it('shows all details of one volume', fakeAsync(async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput('volumes', [
      {
        name: 'Foo',
        devicePath: '/foo/bar',
        fileSystemType: 'test-file-system-type',
        totalSize: BigInt(5 * 1024 * 1024 * 1024),
        bytesPerSector: BigInt(512),
        freeSpace: BigInt(1024 * 1024 * 1024),
        creationTime: new Date('2020-07-01T13:00:00.000Z'),
        unixDetails: {
          mountPoint: '/mount/baz/',
          mountOptions: 'test-mount-options',
        },
        windowsDetails: {
          attributes: ['test-attribute1', 'test-attribute2'],
          driveLetter: 'Z',
          driveType: 'test-drive-type',
        },
      },
    ]);
    tick();

    expect(await harness.hasNoneText()).toBeFalse();
    expect(await harness.numTables()).toBe(1);
    expect(await harness.numRows()).toBe(12);
    const rowTexts = await harness.getRowTexts();

    expect(rowTexts[0]).toContain('Drive Letter');
    expect(rowTexts[0]).toContain('Z');

    expect(rowTexts[1]).toContain('Drive Attributes');
    expect(rowTexts[1]).toContain('test-attribute1');
    expect(rowTexts[1]).toContain('test-attribute2');

    expect(rowTexts[2]).toContain('Drive Type');
    expect(rowTexts[2]).toContain('test-drive-type');

    expect(rowTexts[3]).toContain('Mount Point');
    expect(rowTexts[3]).toContain('/mount/baz/');

    expect(rowTexts[4]).toContain('Mount Options');
    expect(rowTexts[4]).toContain('test-mount-options');

    expect(rowTexts[5]).toContain('Volume Name');
    expect(rowTexts[5]).toContain('Foo');

    expect(rowTexts[6]).toContain('Device Path');
    expect(rowTexts[6]).toContain('/foo/bar');

    expect(rowTexts[7]).toContain('Filesystem Type');
    expect(rowTexts[7]).toContain('test-file-system-type');

    expect(rowTexts[8]).toContain('Total Size');
    expect(rowTexts[8]).toContain('5.00 GiB');

    expect(rowTexts[9]).toContain('Free Space');
    expect(rowTexts[9]).toContain('1.00 GiB');

    expect(rowTexts[10]).toContain('Sector Size');
    expect(rowTexts[10]).toContain('512 B');

    expect(rowTexts[11]).toContain('Creation Time');
    expect(rowTexts[11]).toContain('2020-07-01 13:00:00 UTC');
  }));

  it('skips empty fields', fakeAsync(async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput('volumes', [{}]);
    tick();
    expect(await harness.hasNoneText()).toBeFalse();
    expect(await harness.numTables()).toBe(1);
    expect(await harness.numRows()).toBe(0);
  }));

  it('renders multiple volumes', fakeAsync(async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput('volumes', [
      {
        name: 'Foo',
      },
      {
        name: 'Bar',
      },
      {
        name: 'Baz',
      },
    ]);
    tick();
    expect(await harness.hasNoneText()).toBeFalse();
    expect(await harness.numTables()).toBe(3);
    expect(await harness.numRows()).toBe(3);
  }));
});
