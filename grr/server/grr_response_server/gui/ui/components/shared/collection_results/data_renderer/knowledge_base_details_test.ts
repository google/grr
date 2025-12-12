import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {KnowledgeBase} from '../../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../../testing';
import {KnowledgeBaseDetails} from './knowledge_base_details';
import {KnowledgeBaseDetailsHarness} from './testing/knowledge_base_details_harness';

initTestEnvironment();

async function createComponent(knowledgeBase: KnowledgeBase | undefined) {
  const fixture = TestBed.createComponent(KnowledgeBaseDetails);
  fixture.componentRef.setInput('knowledgeBase', knowledgeBase);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    KnowledgeBaseDetailsHarness,
  );

  return {fixture, harness};
}

describe('Knowledge Base Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [KnowledgeBaseDetails, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent(undefined);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows an empty table if there are no results', async () => {
    const {harness} = await createComponent(undefined);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table.text()).toBe('');
  });

  it('shows a complete knowledge base', async () => {
    const {harness} = await createComponent({
      os: 'Linux',
      osMajorVersion: 6,
      osMinorVersion: 123,
      fqdn: 'foo.bar.com',
    });

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table.text()).toContain('System OS');
    expect(await table.text()).toContain('Linux');
    expect(await table.text()).toContain('OS Major Version');
    expect(await table.text()).toContain('6');
    expect(await table.text()).toContain('OS Minor Version');
    expect(await table.text()).toContain('123');
    expect(await table.text()).toContain('FQDN');
    expect(await table.text()).toContain('foo.bar.com');
  });
});
