import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {getInputValue, isButtonToggleSelected, selectButtonToggle, setInputValue} from '../../../form_testing';
import {HuntState} from '../../../lib/models/hunt';
import {newHunt, newSafetyLimits} from '../../../lib/models/model_test_util';
import {HuntPageGlobalStore} from '../../../store/hunt_page_global_store';
import {HuntPageGlobalStoreMock, mockHuntPageGlobalStore} from '../../../store/hunt_page_global_store_test_util';

import {ModifyHunt} from './modify_hunt';
import {ModifyHuntModule} from './module';

describe('modify hunt', () => {
  let huntPageGlobalStore: HuntPageGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    huntPageGlobalStore = mockHuntPageGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ModifyHuntModule,
          ],
          providers: [
            {
              provide: HuntPageGlobalStore,
              useFactory: () => huntPageGlobalStore,
            },
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('sets form value based on store', async () => {
    const fixture = TestBed.createComponent(ModifyHunt);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
      safetyLimits: newSafetyLimits({
        clientLimit: BigInt(1234),
        clientRate: 5678,
      }),
    }));
    fixture.detectChanges();

    expect(await isButtonToggleSelected(
               fixture, '.rollout-speed-option', 'Custom'))
        .toBe(true);
    expect(await getInputValue(fixture, '[name=clientRate]')).toBe('5678');
    expect(await isButtonToggleSelected(fixture, '.run-on-option', 'Custom'))
        .toBe(true);
    expect(await getInputValue(fixture, '[name=customClientLimit]'))
        .toBe('1234');
  });

  it('button label - not started', async () => {
    const fixture = TestBed.createComponent(ModifyHunt);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
      state: HuntState.NOT_STARTED,
    }));
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Start collection');
  });

  it('button label - reached client limit', async () => {
    const fixture = TestBed.createComponent(ModifyHunt);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
      state: HuntState.REACHED_CLIENT_LIMIT,
    }));
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Continue collection');
  });

  it('pulls store value only once', async () => {
    const fixture = TestBed.createComponent(ModifyHunt);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
      safetyLimits: newSafetyLimits({
        clientLimit: BigInt(1234),
        clientRate: 5678,
      }),
    }));
    fixture.detectChanges();

    expect(await isButtonToggleSelected(
               fixture, '.rollout-speed-option', 'Custom'))
        .toBe(true);
    expect(await getInputValue(fixture, '[name=clientRate]')).toBe('5678');
    expect(await isButtonToggleSelected(fixture, '.run-on-option', 'Custom'))
        .toBe(true);
    expect(await getInputValue(fixture, '[name=customClientLimit]'))
        .toBe('1234');

    huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
      safetyLimits: newSafetyLimits({
        clientLimit: BigInt(999),
        clientRate: 999,
      }),
    }));

    // Form values don't change
    expect(await isButtonToggleSelected(
               fixture, '.rollout-speed-option', 'Custom'))
        .toBe(true);
    expect(await getInputValue(fixture, '[name=clientRate]')).toBe('5678');
    expect(await isButtonToggleSelected(fixture, '.run-on-option', 'Custom'))
        .toBe(true);
    expect(await getInputValue(fixture, '[name=customClientLimit]'))
        .toBe('1234');
  });

  it('calls store method with right params - unlimited', async () => {
    const fixture = TestBed.createComponent(ModifyHunt);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
      safetyLimits: newSafetyLimits({
        clientLimit: BigInt(1234),
        clientRate: 5678,
      }),
    }));
    fixture.detectChanges();

    await selectButtonToggle(fixture, '.rollout-speed-option', 'Unlimited');
    await selectButtonToggle(fixture, '.run-on-option', 'All matching clients');
    fixture.detectChanges();

    expect(await isButtonToggleSelected(
               fixture, '.rollout-speed-option', 'Unlimited'))
        .toBe(true);
    expect(await isButtonToggleSelected(
               fixture, '.run-on-option', 'All matching clients'))
        .toBe(true);

    const modifyAndContinueBtn =
        fixture.debugElement.query(By.css('button[id=modifyAndContinue]'));
    modifyAndContinueBtn.nativeElement.click();
    fixture.detectChanges();

    expect(huntPageGlobalStore.modifyAndStartHunt).toHaveBeenCalledWith({
      clientLimit: BigInt(0),
      clientRate: 0,
    });
  });

  it('calls store method with right params - custom', async () => {
    const fixture = TestBed.createComponent(ModifyHunt);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
      safetyLimits: newSafetyLimits({
        clientLimit: BigInt(0),
        clientRate: 0,
      }),
    }));
    fixture.detectChanges();

    await selectButtonToggle(fixture, '.rollout-speed-option', 'Custom');
    await selectButtonToggle(fixture, '.run-on-option', 'Custom');
    fixture.detectChanges();
    await setInputValue(fixture, '[name=clientRate]', '5678');
    await setInputValue(fixture, '[name=customClientLimit]', '1234');
    fixture.detectChanges();

    expect(await isButtonToggleSelected(
               fixture, '.rollout-speed-option', 'Custom'))
        .toBe(true);
    expect(await isButtonToggleSelected(fixture, '.run-on-option', 'Custom'))
        .toBe(true);

    const modifyAndContinueBtn =
        fixture.debugElement.query(By.css('button[id=modifyAndContinue]'));
    modifyAndContinueBtn.nativeElement.click();
    fixture.detectChanges();

    expect(huntPageGlobalStore.modifyAndStartHunt).toHaveBeenCalledWith({
      clientLimit: BigInt(1234),
      clientRate: 5678,
    });
  });
});
