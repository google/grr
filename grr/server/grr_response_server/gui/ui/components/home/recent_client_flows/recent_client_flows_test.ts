import {Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {provideRouter} from '@angular/router';

import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  newClientApproval,
  newFlow,
  newFlowDescriptorMap,
} from '../../../lib/models/model_test_util';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {
  ConfigGlobalStoreMock,
  mockConfigGlobalStore,
} from '../../../store/config_global_store_test_util';
import {RecentClientFlowsLocalStore} from '../../../store/recent_client_flows_local_store';
import {
  RecentClientFlowsLocalStoreMock,
  mockRecentClientFlowsLocalStore,
} from '../../../store/recent_client_flows_local_store_test_util';
import {STORE_PROVIDERS} from '../../../store/store_test_providers';
import {initTestEnvironment} from '../../../testing';

import {RecentClientFlowsModule} from './module';
import {RecentClientFlows} from './recent_client_flows';

initTestEnvironment();

@Component({standalone: false, template: '', jit: true})
class DummyComponent {}

describe('RecentClientFlows Component', () => {
  let configGlobalStore: ConfigGlobalStoreMock;
  let recentClientFlowsLocalStore: RecentClientFlowsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    configGlobalStore = mockConfigGlobalStore();
    recentClientFlowsLocalStore = mockRecentClientFlowsLocalStore();

    TestBed.configureTestingModule({
      imports: [RecentClientFlowsModule, NoopAnimationsModule],
      declarations: [DummyComponent],
      providers: [
        ...STORE_PROVIDERS,
        {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
        provideRouter([{path: 'clients', component: DummyComponent}]),
      ],
      teardown: {destroyAfterEach: false},
    })
      .overrideProvider(RecentClientFlowsLocalStore, {
        useFactory: () => recentClientFlowsLocalStore,
      })
      .compileComponents();
  }));

  it('displays client information when loaded', () => {
    const fixture = TestBed.createComponent(RecentClientFlows);
    const dummyComponent = fixture.componentInstance;
    dummyComponent.approval = newClientApproval({
      clientId: 'C.1111',
      status: {type: 'valid'},
    });
    recentClientFlowsLocalStore.mockedObservables.hasAccess$.next(true);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('C.1111');
    expect(text).toContain('computer');
    expect(text).toContain('Access granted');

    const link = fixture.debugElement.query(By.css('a'));
    expect(link.attributes['href']).toEqual('/clients/C.1111');
  });

  it('does not display chip when access is inconsistent 1', () => {
    const fixture = TestBed.createComponent(RecentClientFlows);
    const dummyComponent = fixture.componentInstance;
    dummyComponent.approval = newClientApproval({
      clientId: 'C.1111',
      status: {type: 'valid'},
    });
    recentClientFlowsLocalStore.mockedObservables.hasAccess$.next(false);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).not.toContain('Access granted');
  });

  it('does not display chip when access is inconsistent 2', () => {
    const fixture = TestBed.createComponent(RecentClientFlows);
    const dummyComponent = fixture.componentInstance;
    dummyComponent.approval = newClientApproval({
      clientId: 'C.1111',
      status: {type: 'invalid', reason: 'reasons'},
    });
    recentClientFlowsLocalStore.mockedObservables.hasAccess$.next(true);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).not.toContain('Access granted');
  });

  it('displays and loads the top 3 recent client flows', async () => {
    const fixture = TestBed.createComponent(RecentClientFlows);

    fixture.detectChanges();
    fixture.componentInstance.approval = newClientApproval({
      clientId: 'C.1111',
      status: {type: 'valid'},
    });
    fixture.detectChanges();

    expect(recentClientFlowsLocalStore.selectClient).toHaveBeenCalledWith(
      'C.1111',
    );
    configGlobalStore.mockedObservables.flowDescriptors$.next(
      newFlowDescriptorMap(
        {
          name: 'ClientFileFinder',
          friendlyName: 'Client Side File Finder',
        },
        {
          name: 'Kill',
          friendlyName: 'Kill GRR agent process',
        },
      ),
    );

    recentClientFlowsLocalStore.mockedObservables.flowListEntries$.next({
      flows: [
        newFlow({
          name: 'Kill',
          creator: 'ricky',
          clientId: 'C.1111',
        }),
        newFlow({
          name: 'ClientFileFinder',
          creator: 'rick',
          clientId: 'C.1111',
        }),
        newFlow({
          name: 'ClientFileFinder',
          creator: 'bob',
          clientId: 'C.1111',
        }),
      ],
    });
    fixture.detectChanges();

    const flowDetailsCard = fixture.debugElement.queryAll(
      By.css('flow-details'),
    );
    expect(flowDetailsCard.length).toEqual(3);
    expect(flowDetailsCard[0].nativeElement.textContent).toContain('ricky');
    expect(flowDetailsCard[1].nativeElement.textContent).toContain('rick');
    expect(flowDetailsCard[2].nativeElement.textContent).toContain('bob');
  });
});
