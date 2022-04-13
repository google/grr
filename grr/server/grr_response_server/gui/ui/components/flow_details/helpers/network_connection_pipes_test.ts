import {Component, Type} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';

import {initTestEnvironment} from '../../../testing';

import {HelpersModule} from './module';


@Component({template: '{{ value | networkConnectionFamily }}'})
class TestFamilyComponent {
  value: string|undefined;
}

@Component({template: '{{ value | networkConnectionType }}'})
class TestTypeComponent {
  value: string|undefined;
}

initTestEnvironment();

describe('Network Connection Pipes', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            HelpersModule,
          ],
          declarations: [
            TestFamilyComponent,
            TestTypeComponent,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  function render(
      component: Type<TestFamilyComponent|TestTypeComponent>, value?: string) {
    const fixture = TestBed.createComponent(component);
    fixture.componentInstance.value = value;
    fixture.detectChanges();
    return fixture.nativeElement.innerText.trim();
  }

  it('Family - undefined', () => {
    expect(render(TestFamilyComponent, undefined)).toBe('-');
  });

  it('Family - INET', () => {
    expect(render(TestFamilyComponent, 'INET')).toBe('IPv4');
  });

  it('Family - INET6', () => {
    expect(render(TestFamilyComponent, 'INET6')).toBe('IPv6');
  });

  it('Family - INET6_WIN', () => {
    expect(render(TestFamilyComponent, 'INET6_WIN')).toBe('IPv6');
  });

  it('Family - INET6_OSX', () => {
    expect(render(TestFamilyComponent, 'INET6_OSX')).toBe('IPv6');
  });

  it('Type - undefined', () => {
    expect(render(TestTypeComponent, undefined)).toBe('-');
  });

  it('Type - UNKNOWN_SOCKET', () => {
    expect(render(TestTypeComponent, 'UNKNOWN_SOCKET')).toBe('?');
  });

  it('Type - SOCK_STREAM', () => {
    expect(render(TestTypeComponent, 'SOCK_STREAM')).toBe('TCP');
  });

  it('Type - SOCK_DGRAM', () => {
    expect(render(TestTypeComponent, 'SOCK_DGRAM')).toBe('UDP');
  });
});
