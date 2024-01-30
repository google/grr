import {Component, Input} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {BrowserTestingModule} from '@angular/platform-browser/testing';

import {SanitizerPipeModule} from './module';

describe('SanitizerPipe', () => {
  describe('HTML sanitizer context', () => {
    @Component({template: `<div [innerHTML]="htmlSnippet|sanitize"></div>`})
    class TestHostComponent {
      @Input() htmlSnippet?: string;
    }

    beforeEach(() => {
      TestBed.configureTestingModule({
        imports: [SanitizerPipeModule, BrowserTestingModule],
        declarations: [TestHostComponent],
      }).compileComponents();
    });

    it('shows empty if the html snippet is undefined', () => {
      const fixture = TestBed.createComponent(TestHostComponent);

      fixture.componentInstance.htmlSnippet = undefined;

      fixture.detectChanges();

      const text = fixture.debugElement.nativeElement.innerHTML;
      expect(text).toBe('<div></div>');
    });

    it('shows the same content if the html snippet is safe', () => {
      const fixture = TestBed.createComponent(TestHostComponent);

      fixture.componentInstance.htmlSnippet = '<div>Hello</div>';

      fixture.detectChanges();

      const text = fixture.debugElement.nativeElement.innerHTML;
      expect(text).toBe('<div><div>Hello</div></div>');
    });

    it('strips out the unsafe content if it is unsafe', () => {
      const fixture = TestBed.createComponent(TestHostComponent);

      fixture.componentInstance.htmlSnippet =
        '<script type="text/javascript">window.alert("peekaboo")</script>';

      fixture.detectChanges();

      const text = fixture.debugElement.nativeElement.innerHTML;
      expect(text).toBe('<div></div>');
    });
  });
});
