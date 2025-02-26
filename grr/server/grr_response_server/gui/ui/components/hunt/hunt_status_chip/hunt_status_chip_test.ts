import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component, Input} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatTooltipHarness} from '@angular/material/tooltip/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {Duration} from '../../../lib/date_time';
import {HuntState} from '../../../lib/models/hunt';
import {newHunt} from '../../../lib/models/model_test_util';
import {GrrUser} from '../../../lib/models/user';
import {
  injectMockStore,
  STORE_PROVIDERS,
} from '../../../store/store_test_providers';
import {UserGlobalStore} from '../../../store/user_global_store';

import {HuntStatusChip} from './hunt_status_chip';
import {HuntStatusChipModule} from './module';

@Component({
  standalone: false,
  template: `<app-hunt-status-chip [hunt]="hunt"></app-hunt-status-chip>`,
  jit: true,
})
class TestHostComponent {
  @Input() hunt: HuntStatusChip['hunt'] = null;
}

describe('HuntStatusChip', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, HuntStatusChipModule],
      declarations: [TestHostComponent],
      providers: [...STORE_PROVIDERS],
    }).compileComponents();
  }));

  it('shows "Collection not started" for "Not started" hunt APPROVAL', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({state: HuntState.NOT_STARTED});
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'unused_but_required',
      huntApprovalRequired: true,
    } as GrrUser);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collection not started');

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await harnessLoader.getHarness(MatTooltipHarness);
    await harness.show();
    expect(await harness.getTooltipText()).toContain('approval');
  });

  it('shows "Collection not started" for "Not started" hunt', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({state: HuntState.NOT_STARTED});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collection not started');

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await harnessLoader.getHarness(MatTooltipHarness);
    await harness.show();
    expect(await harness.getTooltipText()).not.toContain('approval');
  });

  it('shows correct text for "Reached client limit" hunt', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({
      state: HuntState.REACHED_CLIENT_LIMIT,
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Reached client limit  (200 clients)');
  });

  it('shows "Collection cancelled" for "Cancelled" hunt', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({state: HuntState.CANCELLED});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collection cancelled');

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await harnessLoader.getHarness(MatTooltipHarness);
    await harness.show();
    expect(await harness.getTooltipText()).toEqual('Cancelled by user');
  });

  it('shows default stateComment when empty', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({
      state: HuntState.CANCELLED,
      stateComment: '',
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collection cancelled');

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await harnessLoader.getHarness(MatTooltipHarness);
    await harness.show();
    expect(await harness.getTooltipText()).toEqual('Cancelled by user');
  });

  it('shows CANCELLED stateComment in tooltip', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({
      state: HuntState.CANCELLED,
      stateComment: 'Something went wrong',
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collection cancelled');

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await harnessLoader.getHarness(MatTooltipHarness);
    await harness.show();
    expect(await harness.getTooltipText()).toEqual('Something went wrong');
  });

  it('shows correct text "Collection completed" hunt', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({
      state: HuntState.REACHED_TIME_LIMIT,
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Reached time limit   (32 seconds)');
  });

  it('shows "Collection running" for "Started" hunt', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({state: HuntState.RUNNING});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collection running');
  });

  it('shows "left" for "Started" hunt', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    // 3 days plus buffer to unflake the test.
    const threeDays = Duration.fromObject({day: 3, minute: 1});
    fixture.componentInstance.hunt = newHunt({
      state: HuntState.RUNNING,
      duration: threeDays,
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('3 days left');
  });
});
