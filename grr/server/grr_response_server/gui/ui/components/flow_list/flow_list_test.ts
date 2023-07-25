import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {discardPeriodicTasks, fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {MatSelectHarness} from '@angular/material/select/testing';
import {MatSnackBar} from '@angular/material/snack-bar';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {firstValueFrom} from 'rxjs';

import {FlowListModule} from '../../components/flow_list/module';
import {newFlow, newFlowDescriptorMap} from '../../lib/models/model_test_util';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ClientPageGlobalStoreMock, mockClientPageGlobalStore} from '../../store/client_page_global_store_test_util';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {STORE_PROVIDERS} from '../../store/store_test_providers';
import {DISABLED_TIMESTAMP_REFRESH_TIMER_PROVIDER, initTestEnvironment} from '../../testing';
import {ErrorSnackBar} from '../helpers/error_snackbar/error_snackbar';

import {FlowFilter, FlowList} from './flow_list';

@Component({template: `<router-outlet></router-outlet>`})
class TestHostComponent {
}

initTestEnvironment();

function initFlowList(
    configGlobalStore: ConfigGlobalStoreMock,
    clientPageGlobalStore: ClientPageGlobalStoreMock) {
  configGlobalStore.mockedObservables.flowDescriptors$.next(
      newFlowDescriptorMap(
          {
            name: 'ClientFileFinder',
            friendlyName: 'Client Side File Finder',
          },
          {
            name: 'KeepAlive',
            friendlyName: 'KeepAlive',
          }));
  clientPageGlobalStore.mockedObservables.flowListEntries$.next({
    isLoading: false,
    hasMore: false,
    flows: [
      newFlow({
        name: 'KeepAlive',
        creator: 'morty',
        isRobot: true,
      }),
      newFlow({
        name: 'ClientFileFinder',
        creator: 'rick',
      }),
    ],
  });
}

describe('FlowList Component', () => {
  let configGlobalStore: ConfigGlobalStoreMock;
  let clientPageGlobalStore: ClientPageGlobalStoreMock;
  let snackbar: Partial<MatSnackBar>;

  beforeEach(waitForAsync(() => {
    configGlobalStore = mockConfigGlobalStore();
    clientPageGlobalStore = mockClientPageGlobalStore();
    snackbar = jasmine.createSpyObj('MatSnackBar', ['openFromComponent']);

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowListModule,
            RouterTestingModule.withRoutes([
              {path: 'flows/:flowId', component: FlowList},
            ]),
          ],
          declarations: [TestHostComponent],
          providers: [
            ...STORE_PROVIDERS,
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
            {
              provide: ClientPageGlobalStore,
              useFactory: () => clientPageGlobalStore,
            },
            {provide: MatSnackBar, useFactory: () => snackbar},
            DISABLED_TIMESTAMP_REFRESH_TIMER_PROVIDER,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('loads and displays ALL flows', async () => {
    const fixture = TestBed.createComponent(FlowList);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    const flowFilterHarness = await loader.getHarness(
        MatSelectHarness.with({selector: '[name="flow-filter"]'}));
    await flowFilterHarness.clickOptions({text: FlowFilter.ALL_FLOWS});
    fixture.detectChanges();

    initFlowList(configGlobalStore, clientPageGlobalStore);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('KeepAlive');
    expect(text).toContain('morty');
    expect(text).toContain('Client Side File Finder');
    expect(text).toContain('rick');
  });

  it('loads and displays all HUMAN flows', () => {
    const fixture = TestBed.createComponent(FlowList);
    fixture.detectChanges();
    initFlowList(configGlobalStore, clientPageGlobalStore);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).not.toContain('KeepAlive');
    expect(text).not.toContain('morty');
    expect(text).toContain('Client Side File Finder');
    expect(text).toContain('rick');
  });

  it('loads and displays all ROBOT flows', async () => {
    const fixture = TestBed.createComponent(FlowList);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    const flowFilterHarness = await loader.getHarness(
        MatSelectHarness.with({selector: '[name="flow-filter"]'}));
    await flowFilterHarness.clickOptions({text: FlowFilter.ALL_ROBOT_FLOWS});
    fixture.detectChanges();
    initFlowList(configGlobalStore, clientPageGlobalStore);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('KeepAlive');
    expect(text).toContain('morty');
    expect(text).not.toContain('Client Side File Finder');
    expect(text).not.toContain('rick');
  });

  it('loads and displays Flows with missing FlowDescriptors', () => {
    const fixture = TestBed.createComponent(FlowList);
    fixture.detectChanges();

    // Flows won't be displayed until descriptors are fetched.
    configGlobalStore.mockedObservables.flowDescriptors$.next(
        newFlowDescriptorMap());

    clientPageGlobalStore.mockedObservables.flowListEntries$.next({
      isLoading: false,
      hasMore: false,
      flows: [
        newFlow({
          name: 'KeepAlive',
          creator: 'morty',
        }),
        newFlow({
          name: 'ClientFileFinder',
          creator: 'rick',
        }),
      ]
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('ClientFileFinder');
    expect(text).toContain('KeepAlive');
  });

  it('updates flow list on a change in observable', () => {
    const fixture = TestBed.createComponent(FlowList);
    fixture.detectChanges();

    // Flows won't be displayed until descriptors are fetched.
    configGlobalStore.mockedObservables.flowDescriptors$.next(
        newFlowDescriptorMap());

    clientPageGlobalStore.mockedObservables.flowListEntries$.next({
      isLoading: false,
      hasMore: false,
      flows: [
        newFlow({
          name: 'KeepAlive',
          creator: 'morty',
        }),
      ],
    });
    fixture.detectChanges();

    let text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('KeepAlive');

    clientPageGlobalStore.mockedObservables.flowListEntries$.next({
      isLoading: false,
      hasMore: false,
      flows: [
        newFlow({
          name: 'ClientFileFinder',
          creator: 'rick',
        }),
      ],
    });
    fixture.detectChanges();

    text = fixture.debugElement.nativeElement.textContent;
    expect(text).not.toContain('KeepAlive');
    expect(text).toContain('ClientFileFinder');
  });

  it('shows message when all flows have been loaded', () => {
    const fixture = TestBed.createComponent(FlowList);
    fixture.detectChanges();

    configGlobalStore.mockedObservables.flowDescriptors$.next(
        newFlowDescriptorMap());

    clientPageGlobalStore.mockedObservables.flowListEntries$.next(
        {isLoading: true});
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .not.toContain('No older flows to show');

    clientPageGlobalStore.mockedObservables.flowListEntries$.next(
        {isLoading: false, hasMore: true});
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .not.toContain('No older flows to show');

    clientPageGlobalStore.mockedObservables.flowListEntries$.next(
        {isLoading: false, hasMore: false});
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('No older flows to show');
  });

  it('scrolls to flow that is deep-linked in URL', fakeAsync(async () => {
       const fixture = TestBed.createComponent(TestHostComponent);
       fixture.detectChanges();

       const router = TestBed.inject(Router);
       await router.navigate(['flows', '123']);

       const flowList =
           fixture.debugElement.query(By.directive(FlowList)).componentInstance;
       expect(flowList).toBeTruthy();
       const selectedFlowIdPromise = firstValueFrom(flowList.selectedFlowId$);

       configGlobalStore.mockedObservables.flowDescriptors$.next(
           newFlowDescriptorMap());
       clientPageGlobalStore.mockedObservables.flowListEntries$.next({
         isLoading: false,
         hasMore: true,
         flows: [newFlow({flowId: '123'})]
       });
       fixture.detectChanges();

       const scrollTarget =
           fixture.debugElement.query(By.css('#flow-123')).nativeElement;
       const scrollIntoView = spyOn(scrollTarget, 'scrollIntoView');

       tick();
       expect(await selectedFlowIdPromise).toEqual('123');
       expect(flowList.scrollTarget).toEqual('123');
       expect(scrollIntoView).toHaveBeenCalledOnceWith();

       discardPeriodicTasks();
     }));

  it('loads more flows until deep-linked flow is visible',
     fakeAsync(async () => {
       const fixture = TestBed.createComponent(TestHostComponent);
       fixture.detectChanges();

       const router = TestBed.inject(Router);
       await router.navigate(['flows', '3']);

       const flows = [
         newFlow({flowId: '1'}),
         newFlow({flowId: '2'}),
         newFlow({flowId: '3'}),
       ];

       const flowList =
           fixture.debugElement.query(By.directive(FlowList)).componentInstance;
       expect(flowList).toBeTruthy();
       const selectedFlowIdPromise = firstValueFrom(flowList.selectedFlowId$);

       expect(clientPageGlobalStore.loadMoreFlows)
           .not.toHaveBeenCalledOnceWith();

       configGlobalStore.mockedObservables.flowDescriptors$.next(
           newFlowDescriptorMap());
       clientPageGlobalStore.mockedObservables.flowListEntries$.next(
           {isLoading: false, hasMore: true, flows: [...flows.slice(0, 1)]});
       fixture.detectChanges();

       expect(clientPageGlobalStore.loadMoreFlows).toHaveBeenCalledOnceWith();

       clientPageGlobalStore.mockedObservables.flowListEntries$.next(
           {isLoading: false, hasMore: true, flows: [...flows.slice(0, 2)]});
       fixture.detectChanges();

       expect(clientPageGlobalStore.loadMoreFlows).toHaveBeenCalledTimes(2);

       clientPageGlobalStore.mockedObservables.flowListEntries$.next(
           {isLoading: false, hasMore: false, flows});
       fixture.detectChanges();

       const scrollTarget =
           fixture.debugElement.query(By.css('#flow-3')).nativeElement;
       const scrollIntoView = spyOn(scrollTarget, 'scrollIntoView');

       tick();
       expect(await selectedFlowIdPromise).toEqual('3');
       expect(flowList.scrollTarget).toEqual('3');
       expect(scrollIntoView).toHaveBeenCalledOnceWith();
       expect(clientPageGlobalStore.loadMoreFlows).toHaveBeenCalledTimes(2);

       discardPeriodicTasks();
     }));

  it('shows snackbar if flow cannot be found', fakeAsync(async () => {
       const fixture = TestBed.createComponent(TestHostComponent);
       fixture.detectChanges();

       const router = TestBed.inject(Router);
       await router.navigate(['flows', 'notfoundid']);

       const flows = [newFlow({flowId: '1'}), newFlow({flowId: '2'})];

       const flowList =
           fixture.debugElement.query(By.directive(FlowList)).componentInstance;
       expect(flowList).toBeTruthy();

       configGlobalStore.mockedObservables.flowDescriptors$.next(
           newFlowDescriptorMap());
       clientPageGlobalStore.mockedObservables.flowListEntries$.next(
           {isLoading: false, hasMore: true, flows: [...flows.slice(0, 1)]});
       fixture.detectChanges();

       expect(clientPageGlobalStore.loadMoreFlows).toHaveBeenCalledOnceWith();
       expect(snackbar.openFromComponent).not.toHaveBeenCalled();

       clientPageGlobalStore.mockedObservables.flowListEntries$.next(
           {isLoading: false, hasMore: false, flows});
       fixture.detectChanges();

       tick();
       expect(clientPageGlobalStore.loadMoreFlows).toHaveBeenCalledTimes(1);

       expect(snackbar.openFromComponent)
           .toHaveBeenCalledOnceWith(ErrorSnackBar, jasmine.objectContaining({
             data: jasmine.stringMatching('Did not find flow notfoundid.')
           }));

       // Do not show multiple times even when flows are re-emitted.
       clientPageGlobalStore.mockedObservables.flowListEntries$.next(
           {isLoading: false, hasMore: false, flows});
       fixture.detectChanges();
       tick();

       expect(snackbar.openFromComponent).toHaveBeenCalledTimes(1);

       discardPeriodicTasks();
     }));
});
