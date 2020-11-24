import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {App} from './app';
import {AppModule} from './app_module';


describe('App Component', () => {
  beforeEach(async(() => {
    TestBed
        .configureTestingModule({
          imports: [
            AppModule,
            NoopAnimationsModule,  // This makes test faster and more stable.
            RouterTestingModule,
          ],

        })
        .compileComponents();
  }));

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it(`should have as title 'GRR'`, () => {
    const fixture = TestBed.createComponent(App);
    expect(fixture.componentInstance.title).toBe('GRR');
  });
});
