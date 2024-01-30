import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {initTestEnvironment} from '../../../testing';

import {HuntOriginalReference} from './hunt_original_reference';

initTestEnvironment();

describe('HuntOriginalReference', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [
        NoopAnimationsModule,
        HuntOriginalReference,
        RouterTestingModule,
      ],
      declarations: [],
      providers: [],
    }).compileComponents();
  }));

  describe('title', () => {
    it('NOT SHOWN when has no information', () => {
      const fixture = TestBed.createComponent(HuntOriginalReference);
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).not.toContain('Based on...');
    });

    it('present when has hunt information', () => {
      const fixture = TestBed.createComponent(HuntOriginalReference);
      fixture.componentInstance.huntRef = {huntId: 'H111'};
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).toContain('Based on...');
    });

    it('present when has flow information', () => {
      const fixture = TestBed.createComponent(HuntOriginalReference);
      fixture.componentInstance.flowRef = {flowId: 'F222', clientId: 'C333'};
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).toContain('Based on...');
    });

    it('present when has both hunt and flow information', () => {
      const fixture = TestBed.createComponent(HuntOriginalReference);
      fixture.componentInstance.huntRef = {huntId: 'H111'};
      fixture.componentInstance.flowRef = {flowId: 'F222', clientId: 'C333'};
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).toContain('Based on...');
    });
  });

  it('displays only hunt information', () => {
    const fixture = TestBed.createComponent(HuntOriginalReference);
    fixture.componentInstance.huntRef = {huntId: 'H111'};
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Based on...');
    expect(fixture.nativeElement.textContent).toContain('fleet collection');
    expect(fixture.nativeElement.textContent).toContain('H111');
    expect(fixture.nativeElement.textContent).not.toContain('flow');
  });

  it('displays only flow information', () => {
    const fixture = TestBed.createComponent(HuntOriginalReference);
    fixture.componentInstance.flowRef = {flowId: 'F222', clientId: 'C333'};
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Based on...');
    expect(fixture.nativeElement.textContent).toContain('flow');
    expect(fixture.nativeElement.textContent).toContain('F222');
    expect(fixture.nativeElement.textContent).not.toContain('fleet collection');
  });

  it('displays both hunt and flow', () => {
    const fixture = TestBed.createComponent(HuntOriginalReference);
    fixture.componentInstance.huntRef = {huntId: 'H111'};
    fixture.componentInstance.flowRef = {flowId: 'F222', clientId: 'C333'};
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Based on...');
    expect(fixture.nativeElement.textContent).toContain('fleet collection');
    expect(fixture.nativeElement.textContent).toContain('H111');
    expect(fixture.nativeElement.textContent).toContain('flow');
    expect(fixture.nativeElement.textContent).toContain('F222');
  });
});
