import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {RouterTestingHarness} from '@angular/router/testing';

import {GlobalStore} from '../../store/global_store';
import {newGlobalStoreMock} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {ADMINISTRATION_ROUTES} from '../app/routing';
import {AdministrationPage} from './administration_page';
import {AdministrationPageHarness} from './testing/administration_page_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(AdministrationPage);

  fixture.detectChanges();

  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    AdministrationPageHarness,
  );
  return {fixture, harness};
}

describe('Administration Page Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [
        AdministrationPage,
        RouterModule.forRoot(ADMINISTRATION_ROUTES),
        NoopAnimationsModule,
      ],
      providers: [
        {
          provide: GlobalStore,
          useValue: newGlobalStoreMock(),
        },
      ],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness} = await createComponent();

    expect(harness).toBeDefined();
  });

  it('navigations to artifacts shows ArtifactsAdministration component', async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl('/administration/artifacts');
    const {harness} = await createComponent();

    expect(await harness.isArtifactsAdministrationVisible()).toBeTrue();
  });
});
