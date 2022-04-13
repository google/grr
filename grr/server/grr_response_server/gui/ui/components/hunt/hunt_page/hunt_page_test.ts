import {TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {STORE_PROVIDERS} from '../../../store/store_test_providers';
import {getActivatedChildRoute, initTestEnvironment} from '../../../testing';

import {HuntPage} from './hunt_page';
import {HuntPageModule} from './module';
import {HUNT_PAGE_ROUTES} from './routing';

initTestEnvironment();

describe('hunt view test', () => {
  TestBed
      .configureTestingModule({
        imports: [
          NoopAnimationsModule,
          HuntPageModule,
          RouterTestingModule.withRoutes(HUNT_PAGE_ROUTES),
        ],
        providers: [
          ...STORE_PROVIDERS,
          {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
        ],
        teardown: {destroyAfterEach: false}
      })
      .compileComponents();
  it('renders information when loaded', () => {
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;
    expect(text).toContain('placeholder');
  });
});
