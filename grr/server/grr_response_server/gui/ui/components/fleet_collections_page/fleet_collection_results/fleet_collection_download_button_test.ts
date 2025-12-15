import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {GlobalStore} from '../../../store/global_store';
import {
  GlobalStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FleetCollectionDownloadButton} from './fleet_collection_download_button';
import {FleetCollectionDownloadButtonHarness} from './testing/fleet_collection_download_button_harness';

initTestEnvironment();

async function createComponent(fleetCollectionId: string) {
  const fixture = TestBed.createComponent(FleetCollectionDownloadButton);
  fixture.componentRef.setInput('fleetCollectionId', fleetCollectionId);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionDownloadButtonHarness,
  );
  return {fixture, harness};
}

describe('Fleet Collection Download Button Component', () => {
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [FleetCollectionDownloadButton, NoopAnimationsModule],
      providers: [
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('should be created', async () => {
    const {fixture, harness} = await createComponent('1234');

    expect(fixture.componentInstance).toBeTruthy();
    expect(harness).toBeTruthy();
  });

  it('shows download options', async () => {
    const {harness} = await createComponent('1234');

    expect(await harness.hasDownloadButton()).toBeTrue();
    const downloadMenu = await harness.openDownloadMenu();
    const menuItems = await downloadMenu.getItems();
    expect(menuItems).toHaveSize(5);
    expect(await menuItems[0].getText()).toBe('Download files (Tarball)');
    expect(await menuItems[1].getText()).toBe('Download files (ZIP)');
    expect(await menuItems[2].getText()).toBe('Download CSV');
    expect(await menuItems[3].getText()).toBe('Download YAML');
    expect(await menuItems[4].getText()).toBe('Download SQLite');
  });

  it('has `Copy cli command` option when export command prefix is set', async () => {
    globalStoreMock.exportCommandPrefix = signal('export_command_prefix');
    const {harness} = await createComponent('1234');

    const downloadMenu = await harness.openDownloadMenu();
    const menuItems = await downloadMenu.getItems();
    expect(menuItems).toHaveSize(6);
    expect(await menuItems[5].getText()).toBe('Copy CLI Command');
  });
});
