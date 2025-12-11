import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {KnowledgeBase as ApiKnowledgeBase} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {KnowledgeBases} from './knowledge_bases';
import {KnowledgeBasesHarness} from './testing/knowledge_bases_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(KnowledgeBases);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    KnowledgeBasesHarness,
  );

  return {fixture, harness};
}

describe('Knowledge Bases Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [KnowledgeBases, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows complete knowledge base result', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.KNOWLEDGE_BASE,
        payload: {
          fqdn: 'foo.bar.com',
          os: 'Linux',
          osMajorVersion: 6,
          osMinorVersion: 123,
        } as ApiKnowledgeBase,
      }),
    ]);

    const knowledgeBaseHarnesses =
      await harness.knowledgeBaseDetailsHarnesses();
    expect(knowledgeBaseHarnesses).toHaveSize(1);
    const knowledgeBaseHarness = knowledgeBaseHarnesses[0];
    const table = await knowledgeBaseHarness.table();
    expect(table).toBeDefined();
    expect(await table.text()).toContain('System OS');
    expect(await table.text()).toContain('Linux');
    expect(await table.text()).toContain('OS Major Version');
    expect(await table.text()).toContain('6');
    expect(await table.text()).toContain('OS Minor Version');
    expect(await table.text()).toContain('123');
    expect(await table.text()).toContain('FQDN');
    expect(await table.text()).toContain('foo.bar.com');
  }));

  it('shows multiple file finder results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.KNOWLEDGE_BASE,
        payload: {} as ApiKnowledgeBase,
      }),
      newFlowResult({
        payloadType: PayloadType.KNOWLEDGE_BASE,
        payload: {} as ApiKnowledgeBase,
      }),
    ]);

    const knowledgeBaseHarnesses =
      await harness.knowledgeBaseDetailsHarnesses();
    expect(knowledgeBaseHarnesses).toHaveSize(2);
  }));

  it('shows client id for hunt results', async () => {
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payload: {},
      }),
    ]);

    const clientIds = await harness.clientIds();
    expect(clientIds).toHaveSize(1);
    expect(await clientIds[0].text()).toContain('Client ID: C.1234');
  });

  it('does not show client id for flow results', async () => {
    const {harness} = await createComponent([
      newFlowResult({
        clientId: 'C.1234',
        payload: {},
      }),
    ]);

    const clientIds = await harness.clientIds();
    expect(clientIds).toHaveSize(0);
  });
});
