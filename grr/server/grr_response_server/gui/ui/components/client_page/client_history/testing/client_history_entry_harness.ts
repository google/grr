import {ComponentHarness} from '@angular/cdk/testing';

import {CloudInstanceDetailsHarness} from '../../../shared/collection_results/data_renderer/testing/cloud_instance_details_harness';
import {HardwareInfoDetailsHarness} from '../../../shared/collection_results/data_renderer/testing/hardware_info_details_harness';
import {KnowledgeBaseDetailsHarness} from '../../../shared/collection_results/data_renderer/testing/knowledge_base_details_harness';
import {NetworkInterfacesDetailsHarness} from '../../../shared/collection_results/data_renderer/testing/network_interfaces_details_harness';
import {UsersDetailsHarness} from '../../../shared/collection_results/data_renderer/testing/users_details_harness';
import {VolumesDetailsHarness} from '../../../shared/collection_results/data_renderer/testing/volumes_details_harness';

/** Harness for the ClientHistoryEntry component. */
export class ClientHistoryEntryHarness extends ComponentHarness {
  static hostSelector = 'client-history-entry';

  private readonly snapshotSection = this.locatorForOptional(
    '[name="snapshot-section"]',
  );
  private readonly osSection = this.locatorForOptional('[name="os-section"]');
  readonly knowledgeBaseDetailsHarness = this.locatorForOptional(
    KnowledgeBaseDetailsHarness,
  );
  private readonly userDetailsHarness =
    this.locatorForOptional(UsersDetailsHarness);

  private readonly cloudSection = this.locatorForOptional(
    '[name="cloud-section"]',
  );
  readonly cloudInstanceDetailsHarness = this.locatorForOptional(
    CloudInstanceDetailsHarness,
  );

  private readonly agentSection = this.locatorForOptional(
    '[name="agent-section"]',
  );
  private readonly hardwareSection = this.locatorForOptional(
    '[name="hardware-section"]',
  );
  readonly hardwareInfoDetailsHarness = this.locatorForOptional(
    HardwareInfoDetailsHarness,
  );
  private readonly volumesSection = this.locatorFor('[name="volumes-section"]');
  private readonly volumesHarness = this.locatorForOptional(
    VolumesDetailsHarness,
  );
  private readonly networkSection = this.locatorFor('[name="network-section"]');
  private readonly networkInterfacesHarness = this.locatorForOptional(
    NetworkInterfacesDetailsHarness,
  );

  private readonly startupInfoSection = this.locatorForOptional(
    '.startup-info-section',
  );

  async hasSnapshotSection(): Promise<boolean> {
    return !!(await this.snapshotSection());
  }

  async getSnapshotSectionText(): Promise<string> {
    return (await this.snapshotSection())!.text();
  }

  async hasOsSection(): Promise<boolean> {
    return !!(await this.osSection());
  }

  async getOsSectionText(): Promise<string> {
    return (await this.osSection())!.text();
  }

  async getUserDetailsHarness(): Promise<UsersDetailsHarness> {
    const userDetailsHarness = await this.userDetailsHarness();
    if (!userDetailsHarness) {
      throw new Error('Users details harness is not available');
    }
    return userDetailsHarness;
  }

  async hasCloudSection(): Promise<boolean> {
    return !!(await this.cloudSection());
  }

  async getCloudSectionText(): Promise<string> {
    return (await this.cloudSection())?.text() ?? '';
  }

  async hasAgentSection(): Promise<boolean> {
    return !!(await this.agentSection());
  }

  async getAgentSectionText(): Promise<string> {
    return (await this.agentSection())!.text();
  }

  async hasHardwareSection(): Promise<boolean> {
    return !!(await this.hardwareSection());
  }

  async getHardwareSectionText(): Promise<string> {
    return (await this.hardwareSection())!.text();
  }

  async getVolumesSectionText(): Promise<string> {
    return (await this.volumesSection()).text();
  }

  async getVolumesHarness(): Promise<VolumesDetailsHarness | null> {
    const volumesHarness = await this.volumesHarness();
    if (!volumesHarness) {
      throw new Error('Volumes details harness is not available');
    }
    return volumesHarness;
  }

  async getNetworkSectionText(): Promise<string> {
    return (await this.networkSection()).text();
  }

  async getNetworkInterfacesHarness(): Promise<NetworkInterfacesDetailsHarness | null> {
    const networkInterfacesHarness = await this.networkInterfacesHarness();
    if (!networkInterfacesHarness) {
      throw new Error('Network interfaces details harness is not available');
    }
    return networkInterfacesHarness;
  }

  async hasStartupInfoSection(): Promise<boolean> {
    return !!(await this.startupInfoSection());
  }

  async getStartupInfoSectionText(): Promise<string> {
    return (await this.startupInfoSection())!.text();
  }
}
