import {ComponentHarness} from '@angular/cdk/testing';

import {CloudInstanceDetailsHarness} from '../data_renderer/testing/cloud_instance_details_harness';
import {HardwareInfoDetailsHarness} from '../data_renderer/testing/hardware_info_details_harness';
import {KnowledgeBaseDetailsHarness} from '../data_renderer/testing/knowledge_base_details_harness';
import {NetworkInterfacesDetailsHarness} from '../data_renderer/testing/network_interfaces_details_harness';
import {StartupInfoDetailsHarness} from '../data_renderer/testing/startup_info_details_harness';
import {UsersDetailsHarness} from '../data_renderer/testing/users_details_harness';
import {VolumesDetailsHarness} from '../data_renderer/testing/volumes_details_harness';

/** Harness for the ClientSnapshots component. */
export class ClientSnapshotsHarness extends ComponentHarness {
  static hostSelector = 'client-snapshots';

  readonly clientIds = this.locatorForAll('.client-id-container');

  readonly clientSnapshots = this.locatorForAll('.client-snapshot-table');

  private readonly operatingSystemTables = this.locatorForAll(
    '.operating-system-table',
  );

  private readonly knowledgeBaseDetails = this.locatorForAll(
    KnowledgeBaseDetailsHarness,
  );

  private readonly usersDetails = this.locatorForAll(UsersDetailsHarness);

  private readonly cloudInstanceDetails = this.locatorForAll(
    CloudInstanceDetailsHarness,
  );

  private readonly startupInfoDetails = this.locatorForAll(
    StartupInfoDetailsHarness,
  );

  private readonly hardwareTables = this.locatorForAll('.hardware-table');

  private readonly hardwareInfoDetails = this.locatorForAll(
    HardwareInfoDetailsHarness,
  );

  private readonly volumesDetails = this.locatorForAll(VolumesDetailsHarness);

  private readonly networkInterfacesDetails = this.locatorForAll(
    NetworkInterfacesDetailsHarness,
  );

  async getOperatingSystemTableText(index: number): Promise<string> {
    const operatingSystemTables = await this.operatingSystemTables();
    if (index >= operatingSystemTables.length) {
      throw new Error(
        `Operating system table is not available at index ${index}`,
      );
    }
    return operatingSystemTables[index].text();
  }

  async getKnowledgeBaseDetails(
    index: number,
  ): Promise<KnowledgeBaseDetailsHarness> {
    const knowledgeBaseDetails = await this.knowledgeBaseDetails();
    if (index >= knowledgeBaseDetails.length) {
      throw new Error(
        `Knowledge base details are not available at index ${index}`,
      );
    }
    return knowledgeBaseDetails[index];
  }

  async getUsersDetails(index: number): Promise<UsersDetailsHarness> {
    const usersDetails = await this.usersDetails();
    if (index >= usersDetails.length) {
      throw new Error(`Users details are not available at index ${index}`);
    }
    return usersDetails[index];
  }

  async getCloudInstanceDetails(
    index: number,
  ): Promise<CloudInstanceDetailsHarness> {
    const cloudInstanceDetails = await this.cloudInstanceDetails();
    if (index >= cloudInstanceDetails.length) {
      throw new Error(
        `Cloud instance details are not available at index ${index}`,
      );
    }
    return cloudInstanceDetails[index];
  }

  async getStartupInfoDetails(
    index: number,
  ): Promise<StartupInfoDetailsHarness> {
    const startupInfoDetails = await this.startupInfoDetails();
    if (index >= startupInfoDetails.length) {
      throw new Error(
        `Startup info details are not available at index ${index}`,
      );
    }
    return startupInfoDetails[index];
  }

  async getHardwareTableText(index: number): Promise<string> {
    const hardwareTables = await this.hardwareTables();
    if (index >= hardwareTables.length) {
      throw new Error(`Hardware table is not available at index ${index}`);
    }
    return hardwareTables[index].text();
  }

  async getHardwareInfoDetails(
    index: number,
  ): Promise<HardwareInfoDetailsHarness> {
    const hardwareInfoDetails = await this.hardwareInfoDetails();
    if (index >= hardwareInfoDetails.length) {
      throw new Error(
        `Hardware info details are not available at index ${index}`,
      );
    }
    return hardwareInfoDetails[index];
  }

  async getVolumesDetails(index: number): Promise<VolumesDetailsHarness> {
    const volumesDetails = await this.volumesDetails();
    if (index >= volumesDetails.length) {
      throw new Error(`Volumes details are not available at index ${index}`);
    }
    return volumesDetails[index];
  }

  async getNetworkInterfacesDetails(
    index: number,
  ): Promise<NetworkInterfacesDetailsHarness> {
    const networkInterfacesDetails = await this.networkInterfacesDetails();
    if (index >= networkInterfacesDetails.length) {
      throw new Error(
        `Network interfaces details are not available at index ${index}`,
      );
    }
    return networkInterfacesDetails[index];
  }
}
