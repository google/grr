import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {NewHuntLocalStore} from '../../../../store/new_hunt_local_store';
import {mockNewHuntLocalStore} from '../../../../store/new_hunt_local_store_test_util';
import {injectMockStore, STORE_PROVIDERS} from '../../../../store/store_test_providers';
import {initTestEnvironment} from '../../../../testing';

import {ParamsFormModule} from './module';

import {ParamsForm} from './params_form';

initTestEnvironment();

describe('params form test', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ParamsFormModule,
          ],
          providers: [
            ...STORE_PROVIDERS,
          ],

          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            NewHuntLocalStore, {useFactory: mockNewHuntLocalStore})
        .compileComponents();
  }));

  it('toggles contents on click on toggle button', () => {
    const fixture = TestBed.createComponent(ParamsForm);
    const button = fixture.debugElement.query(By.css('#param-form-toggle'));
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeFalse();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeTrue();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeFalse();
  });

  it('only renders the advanced params when clicking show safety limit', () => {
    const fixture = TestBed.createComponent(ParamsForm);
    fixture.detectChanges();

    const button = fixture.debugElement.query(By.css('#toggle-advance-params'));
    expect(button.nativeElement.textContent)
        .toContain('expand_more Show safety limits ');
    const element =
        fixture.debugElement.query(By.css('.advanced-params')).nativeElement;
    expect(getComputedStyle(element).display).toEqual('none');

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(button.nativeElement.textContent)
        .toContain('expand_less Hide safety limits ');
    expect(getComputedStyle(element).display).not.toEqual('none');
  });

  it('only set the default values of the parameters', async () => {
    const fixture = TestBed.createComponent(ParamsForm);
    fixture.detectChanges();
    const newHuntLocalStore =
        injectMockStore(NewHuntLocalStore, fixture.debugElement);
    newHuntLocalStore.mockedObservables.safetyLimits$.next({
      clientRate: 200.0,
      crashLimit: BigInt(100),
      avgResultsPerClientLimit: BigInt(1000),
      avgCpuSecondsPerClientLimit: BigInt(60),
      avgNetworkBytesPerClientLimit: BigInt(10485760),
      cpuLimit: BigInt(0),
      expiryTime: BigInt(1209600),
      networkBytesLimit: BigInt(0),
    });
    fixture.detectChanges();
    const component = fixture.componentInstance;
    expect(component.form.controls['clientRate'].value).toBe(200.0);
    expect(component.form.controls['expiryTime'].value).toBe(BigInt(1209600));
    expect(component.form.controls['crashLimit'].value).toBe(BigInt(100));
    expect(component.form.controls['avgResultsPerClientLimit'].value)
        .toBe(BigInt(1000));
    expect(component.form.controls['avgCpuSecondsPerClientLimit'].value)
        .toBe(BigInt(60));
    expect(component.form.controls['avgNetworkBytesPerClientLimit'].value)
        .toBe(BigInt(10485760));
  });


  it('only renders custom input when select custom', async () => {
    const fixture = TestBed.createComponent(ParamsForm);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    fixture.detectChanges();
    const clientRate = await loader.getAllHarnesses(
        MatInputHarness.with({selector: '[name=customClientLimit]'}));
    expect(clientRate.length).toBe(0);
    const customClientRateButton = fixture.debugElement.query(By.css('.run-on'))
                                       .children[2]
                                       .query(By.css('button'));
    customClientRateButton.triggerEventHandler(
        'click', new MouseEvent('click'));
    fixture.detectChanges();
    const newClientRate = await loader.getAllHarnesses(
        MatInputHarness.with({selector: '[name=customClientLimit]'}));
    expect(newClientRate.length).toBe(1);
  });
});
