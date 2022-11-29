import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, convertToParamMap, ParamMap, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ReplaySubject} from 'rxjs';

import {ApiModule} from '../../../../lib/api/module';
import {HuntPageGlobalStore} from '../../../../store/hunt_page_global_store';
import {HuntPageGlobalStoreMock, mockHuntPageGlobalStore} from '../../../../store/hunt_page_global_store_test_util';

import {HuntResultDetails} from './hunt_result_details';
import {HuntResultDetailsModule} from './module';
import {HUNT_DETAILS_ROUTES} from './routing';

describe('hunt details', () => {
  let huntPageGlobalStore: HuntPageGlobalStoreMock;
  let activatedRoute: Partial<ActivatedRoute>&
      {paramMap: ReplaySubject<ParamMap>};

  beforeEach(waitForAsync(() => {
    huntPageGlobalStore = mockHuntPageGlobalStore();
    activatedRoute = {
      paramMap: new ReplaySubject<ParamMap>(),
    };

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            HuntResultDetailsModule,
            RouterTestingModule.withRoutes(HUNT_DETAILS_ROUTES),
          ],
          providers: [
            {
              provide: HuntPageGlobalStore,
              useFactory: () => huntPageGlobalStore,
            },
            {provide: ActivatedRoute, useFactory: () => activatedRoute},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    TestBed.inject(Router);
  }));

  it('query store based on route', () => {
    activatedRoute.paramMap.next(
        convertToParamMap({'key': 'C.123-5678-999999999999'}));
    const fixture = TestBed.createComponent(HuntResultDetails);
    fixture.detectChanges();

    expect(huntPageGlobalStore.selectResult)
        .toHaveBeenCalledWith('C.123-5678-999999999999');
  });

  it('displays information from store', () => {
    const fixture = TestBed.createComponent(HuntResultDetails);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHuntResultId$.next(
        'C.123-5678-999999999999');
    huntPageGlobalStore.mockedObservables.selectedHuntResult$.next({
      clientId: 'C.123',
      timestamp: '999999999999',
      payload: {'something': 'is coming'}
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('C.123');
    expect(fixture.nativeElement.innerText).toContain('5678');
    expect(fixture.nativeElement.innerText)
        .toContain('1970-01-12 13:46:39 UTC');
    expect(fixture.nativeElement.innerText).toContain('something');
    expect(fixture.nativeElement.innerText).toContain('is coming');
  });
});
