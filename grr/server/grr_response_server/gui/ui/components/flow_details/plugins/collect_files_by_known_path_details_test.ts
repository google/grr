import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatTabGroupHarness} from '@angular/material/tabs/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {CollectFilesByKnownPathArgs, CollectFilesByKnownPathProgress, CollectFilesByKnownPathResultStatus, PathSpecPathType} from '../../../lib/api/api_interfaces';
import {FlowState} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';

import {CollectFilesByKnownPathDetails} from './collect_files_by_known_path_details';
import {PluginsModule} from './module';


initTestEnvironment();

describe('CollectFilesByKnownPathDetails component', () => {
  let flowResultsLocalStore: FlowResultsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    flowResultsLocalStore = mockFlowResultsLocalStore();
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            PluginsModule,
            RouterTestingModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            FlowResultsLocalStore, {useFactory: () => flowResultsLocalStore})
        .compileComponents();
  }));


  it('shows all results tabs', async () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathDetails);
    const args: CollectFilesByKnownPathArgs = {paths: ['/foo', '/bar']};
    const progress: CollectFilesByKnownPathProgress = {
      numCollected: '2',
      numRawFsAccessRetries: '1',
      numFailed: '2',
    };

    fixture.componentInstance.flow = newFlow({
      name: 'CollectFilesByKnownPath',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next([
      newFlowResult({
        payloadType: 'CollectFilesByKnownPathResult',
        payload: {
          stat: {pathspec: {path: '/foo', pathtype: PathSpecPathType.OS}},
          hash: {
            sha256: 'testhash',
          },
          status: CollectFilesByKnownPathResultStatus.COLLECTED,
        }
      }),
      newFlowResult({
        payloadType: 'CollectFilesByKnownPathResult',
        payload: {
          stat: {pathspec: {path: '/retried', pathtype: PathSpecPathType.NTFS}},
          hash: {
            sha256: 'testhash',
          },
          status: CollectFilesByKnownPathResultStatus.COLLECTED,
        }
      }),
      newFlowResult({
        payloadType: 'CollectFilesByKnownPathResult',
        payload: {
          stat: {pathspec: {path: '/bar', pathtype: PathSpecPathType.OS}},
          status: CollectFilesByKnownPathResultStatus.FAILED,
          error: '#failed'
        }
      }),
      newFlowResult({
        payloadType: 'CollectFilesByKnownPathResult',
        payload: {
          stat: {pathspec: {path: '/baz', pathtype: PathSpecPathType.OS}},
          status: CollectFilesByKnownPathResultStatus.NOT_FOUND,
          error: '#reallyfailed'
        }
      })
    ]);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent)
        .toContain(
            '1 file fetched by parsing the raw disk image with libtsk or libfsntfs.');

    const tabsHarness = await harnessLoader.getHarness(MatTabGroupHarness)
                            .then(group => group.getTabs());
    expect(tabsHarness.length).toEqual(2);

    const successTab = tabsHarness[0];
    expect(await successTab.getLabel()).toBe('2 successful file collections');
    expect(await successTab.isSelected()).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('/foo');
    expect(fixture.nativeElement.textContent).toContain('SHA-256');
    expect(fixture.nativeElement.textContent).toContain('check');
    expect(fixture.nativeElement.textContent).toContain('/retried');
    expect(fixture.nativeElement.textContent).toContain('SHA-256');
    expect(fixture.nativeElement.textContent).toContain('priority_high');

    const errorTab = tabsHarness[1];
    expect(await errorTab.getLabel()).toBe('2 errors');
    expect(await errorTab.isSelected()).toBeFalse();
    await errorTab.select();
    expect(await errorTab.isSelected()).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('/bar');
    expect(fixture.nativeElement.textContent).toContain('#failed');
    expect(fixture.nativeElement.textContent).toContain('Unknown error');
    expect(fixture.nativeElement.textContent).toContain('/baz');
    expect(fixture.nativeElement.textContent).toContain('#reallyfailed');
    expect(fixture.nativeElement.textContent).toContain('File not found');
  });

  it('errors tab not shown when no error', async () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathDetails);
    const args: CollectFilesByKnownPathArgs = {paths: ['/foo']};
    const progress: CollectFilesByKnownPathProgress = {
      numCollected: '1',
    };

    fixture.componentInstance.flow = newFlow({
      name: 'CollectFilesByKnownPath',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next([
      newFlowResult({
        payloadType: 'CollectFilesByKnownPathResult',
        payload: {
          stat: {pathspec: {path: '/foo', pathtype: PathSpecPathType.OS}},
          status: CollectFilesByKnownPathResultStatus.COLLECTED,
        }
      }),
    ]);
    fixture.detectChanges();

    const tabsHarness = await harnessLoader.getHarness(MatTabGroupHarness)
                            .then(group => group.getTabs());
    expect(tabsHarness.length).toEqual(1);

    const successTab = tabsHarness[0];
    expect(await successTab.getLabel()).toBe('1 successful file collection');
    expect(await successTab.isSelected()).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('/foo');
    expect(fixture.nativeElement.textContent).toContain('check');
  });

  it('success tab not shown when no success', async () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathDetails);
    const args: CollectFilesByKnownPathArgs = {paths: ['/foo']};
    const progress: CollectFilesByKnownPathProgress = {
      numFailed: '1',
    };

    fixture.componentInstance.flow = newFlow({
      name: 'CollectFilesByKnownPath',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next([
      newFlowResult({
        payloadType: 'CollectFilesByKnownPathResult',
        payload: {
          stat: {pathspec: {path: '/bar', pathtype: PathSpecPathType.OS}},
          status: CollectFilesByKnownPathResultStatus.FAILED,
          error: '#failed'
        }
      }),
    ]);
    fixture.detectChanges();

    const tabsHarness = await harnessLoader.getHarness(MatTabGroupHarness)
                            .then(group => group.getTabs());
    expect(tabsHarness.length).toEqual(1);

    const errorTab = tabsHarness[0];
    expect(await errorTab.getLabel()).toBe('1 error');
    expect(await errorTab.isSelected()).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('/bar');
  });

  it('tab labels use correct counts and plural forms', async () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathDetails);
    const args: CollectFilesByKnownPathArgs = {paths: ['/foo']};
    const progress: CollectFilesByKnownPathProgress = {
      numCollected: '2',
      numRawFsAccessRetries: '3',
      numFailed: '4',
    };

    fixture.componentInstance.flow = newFlow({
      name: 'CollectFilesByKnownPath',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    expect(fixture.nativeElement.textContent)
        .toContain(
            '3 files fetched by parsing the raw disk image with libtsk or libfsntfs.');

    fixture.detectChanges();

    const tabsHarness = await harnessLoader.getHarness(MatTabGroupHarness)
                            .then(group => group.getTabs());
    expect(tabsHarness.length).toEqual(2);

    const successTab = tabsHarness[0];
    expect(await successTab.getLabel()).toBe('2 successful file collections');

    const errorTab = tabsHarness[1];
    expect(await errorTab.getLabel()).toBe('4 errors');
  });

  it('tab labels use correct counts and singular form', async () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathDetails);
    const args: CollectFilesByKnownPathArgs = {paths: ['/foo']};
    const progress: CollectFilesByKnownPathProgress = {
      numCollected: '1',
      numRawFsAccessRetries: '1',
      numFailed: '1',
    };

    fixture.componentInstance.flow = newFlow({
      name: 'CollectFilesByKnownPath',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    expect(fixture.nativeElement.textContent)
        .toContain(
            '1 file fetched by parsing the raw disk image with libtsk or libfsntfs.');

    fixture.detectChanges();

    const tabsHarness = await harnessLoader.getHarness(MatTabGroupHarness)
                            .then(group => group.getTabs());
    expect(tabsHarness.length).toEqual(2);

    const successTab = tabsHarness[0];
    expect(await successTab.getLabel()).toBe('1 successful file collection');

    const errorTab = tabsHarness[1];
    expect(await errorTab.getLabel()).toBe('1 error');
  });

  it('shows file download button', () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathDetails);
    const args: CollectFilesByKnownPathArgs = {paths: ['/foo/**']};
    const progress: CollectFilesByKnownPathProgress = {
      numCollected: '42',
    };

    fixture.componentInstance.flow = newFlow({
      name: 'CollectFilesByKnownPath',
      args,
      progress,
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    const menuItems = fixture.componentInstance.getExportMenuItems(
        fixture.componentInstance.flow);
    expect(menuItems[0])
        .toEqual(fixture.componentInstance.getDownloadFilesExportMenuItem(
            fixture.componentInstance.flow));
    expect(menuItems[0].url)
        .toMatch('/api/v2/clients/.+/flows/.+/results/files-archive');
  });
});
