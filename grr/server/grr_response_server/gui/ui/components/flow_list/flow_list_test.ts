import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';
import {FlowListModule} from '@app/components/flow_list/module';
import {Client} from '@app/lib/models/client';
import {FlowListEntry} from '@app/lib/models/flow';
import {newFlowDescriptorMap, newFlowListEntry} from '@app/lib/models/model_test_util';
import {ClientPageFacade} from '@app/store/client_page_facade';
import {ConfigFacade} from '@app/store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '@app/store/config_facade_test_util';
import {initTestEnvironment} from '@app/testing';
import {ReplaySubject, Subject} from 'rxjs';

import {FlowList} from './flow_list';




initTestEnvironment();

describe('FlowList Component', () => {
  let flowListEntries$: Subject<ReadonlyArray<FlowListEntry>>;
  let selectedClient$: ReplaySubject<Client>;
  let configFacade: ConfigFacadeMock;
  let clientPageFacade: Partial<ClientPageFacade>;

  beforeEach(waitForAsync(() => {
    flowListEntries$ = new Subject();
    selectedClient$ = new ReplaySubject(1);
    configFacade = mockConfigFacade();
    clientPageFacade = {
      flowListEntries$,
      selectedClient$,
    };

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowListModule,
            RouterTestingModule.withRoutes([]),
          ],

          providers: [
            {provide: ConfigFacade, useValue: configFacade},
            {provide: ClientPageFacade, useValue: clientPageFacade},
          ]
        })
        .compileComponents();
  }));

  it('loads and displays Flows', () => {
    const fixture = TestBed.createComponent(FlowList);
    fixture.detectChanges();

    configFacade.flowDescriptorsSubject.next(newFlowDescriptorMap(
        {
          name: 'ClientFileFinder',
          friendlyName: 'Client Side File Finder',
        },
        {
          name: 'KeepAlive',
          friendlyName: 'KeepAlive',
        }));
    flowListEntries$.next([
      newFlowListEntry({
        name: 'KeepAlive',
        creator: 'morty',
      }),
      newFlowListEntry({
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
    configFacade.flowDescriptorsSubject.next(newFlowDescriptorMap());

    flowListEntries$.next([
      newFlowListEntry({
        name: 'KeepAlive',
        creator: 'morty',
      }),
      newFlowListEntry({
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
    configFacade.flowDescriptorsSubject.next(newFlowDescriptorMap());

    flowListEntries$.next([
      newFlowListEntry({
        name: 'KeepAlive',
        creator: 'morty',
      }),
    ]);
    fixture.detectChanges();

    let text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('KeepAlive');

    flowListEntries$.next([
      newFlowListEntry({
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
