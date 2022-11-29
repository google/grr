import {TestBed} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';

import {TextWithLinks} from './text_with_links';
import {TextWithLinksModule} from './text_with_links_module';


initTestEnvironment();

describe('TextWithLinks Component', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        NoopAnimationsModule,
        TextWithLinksModule,
      ],
    });
  });

  it('accepts undefined and null as text input', () => {
    const fixture = TestBed.createComponent(TextWithLinks);
    fixture.componentInstance.text = null;
    fixture.detectChanges();

    let text = fixture.debugElement.nativeElement.textContent;
    expect(text).toEqual('');

    fixture.componentInstance.text = undefined;
    fixture.detectChanges();

    text = fixture.debugElement.nativeElement.textContent;
    expect(text).toEqual('');
  });

  it('linkifies tokens starting with https://', () => {
    const fixture = TestBed.createComponent(TextWithLinks);
    fixture.componentInstance.text = 'test https://example.com test';
    fixture.detectChanges();

    const link = fixture.debugElement.query(By.css('a'));
    expect(link.attributes['href']).toEqual('https://example.com');
    expect(link.nativeElement.textContent).toEqual('https://example.com');

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toEqual('test https://example.com test');
  });

  it('linkifies tokens starting with http://', () => {
    const fixture = TestBed.createComponent(TextWithLinks);
    fixture.componentInstance.text = 'test http://example.com test';
    fixture.detectChanges();

    const link = fixture.debugElement.query(By.css('a'));
    expect(link.attributes['href']).toEqual('http://example.com');
    expect(link.nativeElement.textContent).toEqual('http://example.com');

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toEqual('test http://example.com test');
  });

  it('does not linkify tokens not starting with http:// or https://', () => {
    const fixture = TestBed.createComponent(TextWithLinks);
    fixture.componentInstance.text = 'test google.com test';
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('a'))).toBeNull();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toEqual('test google.com test');
  });
});