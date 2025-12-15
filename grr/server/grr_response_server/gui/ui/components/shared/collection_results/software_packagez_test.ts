import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {SoftwarePackages as ApiSoftwarePackages} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {SoftwarePackagez} from './software_packagez';
import {SoftwarePackagezHarness} from './testing/software_packagez_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(SoftwarePackagez);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    SoftwarePackagezHarness,
  );

  return {fixture, harness};
}

describe('Software Packagez Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [SoftwarePackagez, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows no table if there are no results', fakeAsync(async () => {
    const {harness} = await createComponent([]);

    expect(await harness.table()).toBeNull();
  }));

  it('shows a single software package', fakeAsync(async () => {
    const packages: ApiSoftwarePackages = {
      packages: [
        {
          name: 'FOO',
          version: 'test-version',
          architecture: 'test-architecture',
          publisher: 'test-publisher',
          installedOn: '1600000000000000',
          installedBy: 'test-user',
          sourceRpm: 'test-rpm',
          sourceDeb: 'test-deb',
        },
      ],
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.SOFTWARE_PACKAGES,
        payload: packages,
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(1);
    expect(await harness.getNumCells(0)).toBe(8);
    expect(await harness.getCellText(0, 'name')).toContain('FOO');
    expect(await harness.getCellText(0, 'version')).toContain('test-version');
    expect(await harness.getCellText(0, 'architecture')).toContain(
      'test-architecture',
    );
    expect(await harness.getCellText(0, 'publisher')).toContain(
      'test-publisher',
    );
    expect(await harness.getCellText(0, 'installedOn')).toContain(
      '2020-09-13 12:26:40 UTC',
    );
    expect(await harness.getCellText(0, 'installedBy')).toContain('test-user');
    expect(await harness.getCellText(0, 'sourceRpm')).toContain('test-rpm');
    expect(await harness.getCellText(0, 'sourceDeb')).toContain('test-deb');
  }));

  it('shows multiple flow results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.SOFTWARE_PACKAGES,
        payload: {packages: [{name: 'name-1'}]},
      }),
      newFlowResult({
        payloadType: PayloadType.SOFTWARE_PACKAGES,
        payload: {packages: [{name: 'name-2'}]},
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(2);
  }));

  it('shows client id column for hunt results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payloadType: PayloadType.SOFTWARE_PACKAGES,
        payload: {packages: [{name: 'name-1'}]},
      }),
    ]);

    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
  }));
});
