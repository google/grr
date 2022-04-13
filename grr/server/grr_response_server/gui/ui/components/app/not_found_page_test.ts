import {TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {STORE_PROVIDERS} from '../../store/store_test_providers';

import {AppModule} from './app_module';
import {NotFoundPage} from './not_found_page';

describe('NotFoundPage Component', () => {
  beforeEach((() => {
    TestBed
        .configureTestingModule({
          imports: [
            AppModule, RouterTestingModule,
            NoopAnimationsModule,  // This makes test faster and more stable.
          ],
          providers: [
            ...STORE_PROVIDERS,
          ],
        })
        .compileComponents();
  }));

  it('should be created', () => {
    const fixture = TestBed.createComponent(NotFoundPage);
    expect(fixture.componentInstance).toBeTruthy();
    expect(fixture.debugElement.nativeElement.textContent).toContain('found');
  });
});
