import {async, TestBed} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';
import {HomeModule} from './module';

import {SearchBox} from './search_box';



initTestEnvironment();

describe('SearchBox Component', () => {
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


  it('creates the component', () => {
    const fixture = TestBed.createComponent(SearchBox);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('emits event when query is typed and Enter is pressed', () => {
    const fixture = TestBed.createComponent(SearchBox);
    // Make sure ngAfterViewInit hook gets processed.
    fixture.detectChanges();

    const componentInstance = fixture.componentInstance;
    const emitSpy = spyOn(componentInstance.querySubmitted, 'emit');

    componentInstance.inputFormControl.setValue('foo');
    const debugElement = fixture.debugElement.query(By.css('input'));
    (debugElement.nativeElement as HTMLInputElement)
        .dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter'}));
    fixture.detectChanges();

    expect(emitSpy).toHaveBeenCalledWith('foo');
  });

  it('does not emit event on enter when query is empty', () => {
    const fixture = TestBed.createComponent(SearchBox);
    // Make sure ngAfterViewInit hook gets processed.
    fixture.detectChanges();

    const componentInstance = fixture.componentInstance;
    const emitSpy = spyOn(componentInstance.querySubmitted, 'emit');

    const debugElement = fixture.debugElement.query(By.css('input'));
    (debugElement.nativeElement as HTMLInputElement)
        .dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter'}));
    fixture.detectChanges();

    expect(emitSpy).not.toHaveBeenCalled();
  });
});
