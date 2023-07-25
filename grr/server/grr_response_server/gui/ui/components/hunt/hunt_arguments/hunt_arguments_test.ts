import {Component} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {newClientRuleSet, newHunt, newSafetyLimits} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';

import {HuntArguments} from './hunt_arguments';

initTestEnvironment();

@Component({template: '<hunt-arguments [hunt]="hunt"></hunt-arguments>'})
class TestHostComponent {
  hunt = newHunt({});
}

describe('HuntArguments test', () => {
  beforeEach(async () => {
    await TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HuntArguments,
          ],
          declarations: [
            TestHostComponent,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  });

  it('displays all sections correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
    const TWO_DAYS = 2 * 24 * 60 * 60;

    fixture.componentInstance.hunt = newHunt({
      clientRuleSet: newClientRuleSet({}),
      safetyLimits: newSafetyLimits({
        clientRate: 200,
        clientLimit: BigInt(0),
        avgResultsPerClientLimit: BigInt(20),
        avgCpuSecondsPerClientLimit: BigInt(40),
        avgNetworkBytesPerClientLimit: BigInt(80),
        perClientCpuLimit: BigInt(60 * 2),
        perClientNetworkBytesLimit: BigInt(60),
        expiryTime: BigInt(TWO_DAYS),
      }),
    });
    fixture.detectChanges();

    expect(fixture.nativeElement).toBeTruthy();
    const text = fixture.nativeElement.textContent;

    expect(text).toContain('match any (or)');
    expect(text).toContain('match any:foo, bar');
    expect(text).toContain('Greater Than:123');
    expect(text).toContain('I am a regex');

    expect(text).toContain('200 clients/min (standard)');
    expect(text).toContain('All matching clients');
    expect(text).toContain('2 days');

    expect(text).toContain('55 clients');
    expect(text).toContain('20');
    expect(text).toContain('40 s');
    expect(text).toContain('80 B');

    expect(text).toContain('2 minutes');
    expect(text).toContain('60 B');
  });
});
