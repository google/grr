import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {MatButtonToggleHarness} from '@angular/material/button-toggle/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {firstValueFrom} from 'rxjs';

import {FlowArgsFormModule} from '../../components/flow_args_form/module';
import {latestValueFrom} from '../../lib/reactive';
import {initTestEnvironment} from '../../testing';

import {YaraProcessScanForm} from './yara_process_scan_form';

initTestEnvironment();

describe('YaraProcessScanForm', () => {
  beforeEach(waitForAsync(() => {
    return TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ReactiveFormsModule,
            FlowArgsFormModule,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('shows a PID input field', async () => {
    const fixture = TestBed.createComponent(YaraProcessScanForm);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const toggle = await harnessLoader.getHarness(
        MatButtonToggleHarness.with({text: 'PID'}));
    await toggle.check();

    const args = firstValueFrom(fixture.componentInstance.flowArgs$);

    const input = fixture.debugElement.query(By.css('input[name=pids]'));
    input.nativeElement.value = '123,456';
    input.triggerEventHandler('change', {target: input.nativeElement});
    fixture.detectChanges();

    expect(await args).toEqual(jasmine.objectContaining({
      pids: ['123', '456']
    }));
  });

  it('shows a process name input field', async () => {
    const fixture = TestBed.createComponent(YaraProcessScanForm);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const toggle = await harnessLoader.getHarness(
        MatButtonToggleHarness.with({text: 'Name'}));
    await toggle.check();
    fixture.detectChanges();

    const latestValue = latestValueFrom(fixture.componentInstance.flowArgs$);

    const input =
        fixture.debugElement.query(By.css('input[name=processRegex]'));
    input.nativeElement.value = 'foo';
    input.triggerEventHandler('input', {target: input.nativeElement});
    fixture.detectChanges();

    expect(latestValue.get()).toEqual(jasmine.objectContaining({
      processRegex: 'foo'
    }));
  });

  it('shows a process cmdline input field', async () => {
    const fixture = TestBed.createComponent(YaraProcessScanForm);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const toggle = await harnessLoader.getHarness(
        MatButtonToggleHarness.with({text: 'Cmdline'}));
    await toggle.check();

    const latestValue = latestValueFrom(fixture.componentInstance.flowArgs$);

    const input =
        fixture.debugElement.query(By.css('input[name=cmdlineRegex]'));
    input.nativeElement.value = 'foo';
    input.triggerEventHandler('input', {target: input.nativeElement});
    fixture.detectChanges();

    expect(latestValue.get()).toEqual(jasmine.objectContaining({
      cmdlineRegex: 'foo'
    }));
  });
});
