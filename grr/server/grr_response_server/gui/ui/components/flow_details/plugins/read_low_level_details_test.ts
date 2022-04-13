import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';

import {FlowState} from '../../../lib/models/flow';
import {newFlow} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';

import {PluginsModule} from './module';
import {ReadLowLevelDetails} from './read_low_level_details';


initTestEnvironment();

describe('ReadLowLevelDetails component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            PluginsModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('displays summary in title WITHOUT offset', () => {
    const fixture = TestBed.createComponent(ReadLowLevelDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {path: '/some/path', length: 10},
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText)
        .toContain('10 bytes from /some/path');
  });

  it('displays summary in title WITH offset', () => {
    const fixture = TestBed.createComponent(ReadLowLevelDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {path: '/some/path', length: 10, offset: 6},
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText)
        .toContain('10 bytes starting at 6 from /some/path');
  });

  it('displays args when opened', async () => {
    const fixture = TestBed.createComponent(ReadLowLevelDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {path: '/some/path', length: 123, offset: 321},
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Path: /some/path');
    expect(fixture.nativeElement.innerText).toContain('Length: 123');
    expect(fixture.nativeElement.innerText).toContain('Offset: 321');
  });

  it('displays download button with correct link', () => {
    const fixture = TestBed.createComponent(ReadLowLevelDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      clientId: 'C.1234',
      flowId: '456',
      args: {path: '/some/path', length: 10},
    });
    fixture.detectChanges();

    expect(fixture.componentInstance
               .getExportMenuItems(fixture.componentInstance.flow)[0]
               .url)
        .toEqual('/api/v2/clients/C.1234/vfs-blob/temp/C.1234_456_somepath');
  });
});
