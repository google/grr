import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';
import {FlowListModule} from '@app/components/flow_list/module';
import {newFlow, newFlowDescriptorMap} from '@app/lib/models/model_test_util';
import {ClientPageGlobalStore} from '@app/store/client_page_global_store';
import {ConfigGlobalStore} from '@app/store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '@app/store/config_global_store_test_util';
import {initTestEnvironment} from '@app/testing';

import {ClientPageGlobalStoreMock, mockClientPageGlobalStore} from '../../store/client_page_global_store_test_util';

import {FlowList} from './flow_list';




initTestEnvironment();

describe('FlowList Component', () => {
  let configGlobalStore: ConfigGlobalStoreMock;
  let clientPageGlobalStore: ClientPageGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    configGlobalStore = mockConfigGlobalStore();
    clientPageGlobalStore = mockClientPageGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowListModule,
            RouterTestingModule.withRoutes([]),
          ],

          providers: [
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
            {
              provide: ClientPageGlobalStore,
              useFactory: () => clientPageGlobalStore,
            },
          ]
        })
        .compileComponents();
  }));

  it('loads and displays Flows', () => {
    const fixture = TestBed.createComponent(FlowList);
    fixture.detectChanges();

    configGlobalStore.flowDescriptorsSubject.next(newFlowDescriptorMap(
        {
          name: 'ClientFileFinder',
          friendlyName: 'Client Side File Finder',
        },
        {
          name: 'KeepAlive',
          friendlyName: 'KeepAlive',
        }));
    clientPageGlobalStore.flowListEntriesSubject.next([
      newFlow({
        name: 'KeepAlive',
        creator: 'morty',
      }),
      newFlow({
        name: 'ClientFileFinder',
        creator: 'rick',
      }),
    ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Client Side File Finder');
    expect(text).toContain('morty');
    expect(text).toContain('KeepAlive');
    expect(text).toContain('rick');
  });

  it('loads and displays Flows with missing FlowDescriptors', () => {
    const fixture = TestBed.createComponent(FlowList);
    fixture.detectChanges();

    // Flows won't be displayed until descriptors are fetched.
    configGlobalStore.flowDescriptorsSubject.next(newFlowDescriptorMap());

    clientPageGlobalStore.flowListEntriesSubject.next([
      newFlow({
        name: 'KeepAlive',
        creator: 'morty',
      }),
      newFlow({
        name: 'ClientFileFinder',
        creator: 'rick',
      }),
    ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('ClientFileFinder');
    expect(text).toContain('KeepAlive');
  });

  it('updates flow list on a change in observable', () => {
    const fixture = TestBed.createComponent(FlowList);
    fixture.detectChanges();

    // Flows won't be displayed until descriptors are fetched.
    configGlobalStore.flowDescriptorsSubject.next(newFlowDescriptorMap());

    clientPageGlobalStore.flowListEntriesSubject.next([
      newFlow({
        name: 'KeepAlive',
        creator: 'morty',
      }),
    ]);
    fixture.detectChanges();

    let text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('KeepAlive');

    clientPageGlobalStore.flowListEntriesSubject.next([
      newFlow({
        name: 'ClientFileFinder',
        creator: 'rick',
      }),
    ]);
    fixture.detectChanges();

    text = fixture.debugElement.nativeElement.textContent;
    expect(text).not.toContain('KeepAlive');
    expect(text).toContain('ClientFileFinder');
  });
});
