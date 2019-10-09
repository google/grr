import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../testing';

import {HomeComponent} from './home';
import {HomeModule} from './module';


initTestEnvironment();

describe('Home Component', () => {
  beforeEach(async(() => {
    TestBed
        .configureTestingModule({
          imports: [
            HomeModule,
            NoopAnimationsModule,  // This makes test faster and more stable.
          ],

        })
        .compileComponents();
  }));

  it('should create the component', () => {
    const fixture = TestBed.createComponent(HomeComponent);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it(`should contain string 'GRR'`, () => {
    const fixture = TestBed.createComponent(HomeComponent);
    expect(fixture.nativeElement.textContent).toContain('GRR');
  });
});
