import {Component} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  ForemanClientRuleType,
  ForemanLabelClientRuleMatchMode,
} from '../../../lib/api/api_interfaces';
import {
  newClientRuleSet,
  newHunt,
  newSafetyLimits,
} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';

import {HuntArguments} from './hunt_arguments';

initTestEnvironment();

@Component({
  standalone: false,
  template: '<hunt-arguments [hunt]="hunt"></hunt-arguments>',
  jit: true,
})
class TestHostComponent {
  hunt = newHunt({});
}

describe('HuntArguments test', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, HuntArguments],
      declarations: [TestHostComponent],
      providers: [],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
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
    expect(text).toContain('Greater Than:1337');
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
    expect(text).not.toContain('Unlimited');
  });

  it('displays unlimited client constraints correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({
      clientRuleSet: newClientRuleSet({}),
      safetyLimits: newSafetyLimits({
        perClientNetworkBytesLimit: BigInt(0),
        perClientCpuLimit: BigInt(0),
      }),
    });
    fixture.detectChanges();

    expect(fixture.nativeElement).toBeTruthy();
    const text = fixture.nativeElement.textContent;

    expect(text).not.toContain('345 seconds');
    expect(text).not.toContain('345 B');
    expect(text).toContain('Unlimited');
  });

  it('default match mode and rule type are displayed correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.hunt = newHunt({
      clientRuleSet: newClientRuleSet({
        matchMode: undefined,
        rules: [
          {
            ruleType: ForemanClientRuleType.LABEL,
            label: {
              labelNames: ['foo', 'bar'],
              matchMode: ForemanLabelClientRuleMatchMode.MATCH_ANY,
            },
          },
          {
            os: {osWindows: true, osLinux: true, osDarwin: false},
          },
        ],
      }),
    });
    fixture.detectChanges();

    expect(fixture.nativeElement).toBeTruthy();
    const text = fixture.nativeElement.textContent;

    expect(text).toContain('match all (and)');
    expect(text).toContain('match any:foo, bar');
    expect(text).toContain('Windows');
    expect(text).toContain('Linux');
  });
});
