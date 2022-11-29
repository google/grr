import {ApiClient, CloudInstanceInstanceType, NetworkAddressFamily, WindowsVolumeWindowsDriveTypeEnum, WindowsVolumeWindowsVolumeAttributeEnum} from '../../lib/api/api_interfaces';
import {Client} from '../../lib/models/client';
import {initTestEnvironment} from '../../testing';
import {newClient} from '../models/model_test_util';

import {translateClient} from './client';


initTestEnvironment();

describe('Client API Translation', () => {
  it('converts all client fields correctly', () => {
    const apiClient: ApiClient = {
      clientId: 'C.1234',
      fleetspeakEnabled: true,
      knowledgeBase: {
        fqdn: 'foo.bar',
        os: 'Linux',
        osMajorVersion: 10,
        osMinorVersion: 12,
      },
      osInfo: {
        system: 'Linux',
        node: 'node1',
        release: 'release1',
        version: 'version1',
        machine: 'x86_64',
        kernel: 'Linux',
        fqdn: 'foo.bar',
        installDate: '1571789986678000',
        libcVer: '10',
        architecture: 'x86_64',
      },
      agentInfo: {
        clientName: 'foo',
        clientBinaryName: 'bar',
        clientDescription: 'awesome client',
        clientVersion: 100,
        buildTime: 'Unknown',
        revision: '9',
        timelineBtimeSupport: true,
        sandboxSupport: true,
      },
      volumes: [{
        name: 'A',
        devicePath: '/foo/bar',
        fileSystemType: 'NTFS',
        bytesPerSector: '4096',
        actualAvailableAllocationUnits: '100000',
        sectorsPerAllocationUnit: '1',
        totalAllocationUnits: '1000000',
        creationTime: '1571789496679000',
        unixvolume: {mountPoint: '/', options: 'readonly'},
        windowsvolume: {
          attributesList: [WindowsVolumeWindowsVolumeAttributeEnum.READONLY],
          driveLetter: 'D',
          driveType: WindowsVolumeWindowsDriveTypeEnum.DRIVE_CDROM,
        },
      }],
      interfaces: [{
        macAddress: 'qqusra6v',
        ifname: 'lo',
        addresses: [
          {addressType: NetworkAddressFamily.INET, packedBytes: 'gAAAAQ=='},
          {
            addressType: NetworkAddressFamily.INET6,
            packedBytes: '8AAAAAAAAAAAAAAAAAAAAQ=='
          },
        ],
      }],
      users: [{
        username: 'foo.bar',
        fullName: 'Foo Bar',
        lastLogon: '1571789996679000',
        homedir: '/home/foobar',
        uid: 123,
        gid: 234,
        shell: '/bin/bash',
      }],
      cloudInstance: {
        cloudType: 'GOOGLE' as CloudInstanceInstanceType,
        google: {
          hostname: 'hostname',
          instanceId: '123',
          machineType: 'm1',
          projectId: 'p1',
          uniqueId: 'uniq1',
          zone: 'z1',
        },
        amazon: {
          amiId: 'ami1',
          hostname: 'hostname',
          instanceId: 'instance1',
          instanceType: 'm1',
          publicHostname: 'publichostname',
        },
      },
      hardwareInfo: {
        serialNumber: 'serialNumber1',
        systemManufacturer: 'systemManufacturer1',
        systemProductName: 'systemProductName1',
        systemUuid: 'systemUuid1',
        systemSkuNumber: 'systemSkuNumber1',
        systemFamily: 'systemFamily1',
        biosVendor: 'biosVendor1',
        biosVersion: 'biosVersion1',
        biosReleaseDate: 'biosReleaseDate1',
        biosRomSize: 'biosRomSize1',
        biosRevision: 'biosRevision1',
        systemAssettag: 'systemAssettag1',
      },
      memorySize: '1234',
      firstSeenAt: '1571789996678000',
      lastSeenAt: '1571789996679000',
      lastBootedAt: '1571789996680000',
      lastClock: '1571789996681000',
      labels: [
        {name: 'a', owner: 'ao'},
        {name: 'b', owner: 'bo'},
      ],
      age: '1571789996678000',
      sourceFlowId: 'f123',
    };
    const client: Client = newClient({
      clientId: 'C.1234',
      fleetspeakEnabled: true,
      knowledgeBase: {
        fqdn: 'foo.bar',
        os: 'Linux',
        osMajorVersion: 10,
        osMinorVersion: 12,
      },
      agentInfo: {
        clientName: 'foo',
        clientBinaryName: 'bar',
        clientDescription: 'awesome client',
        clientVersion: 100,
        revision: BigInt(9),
        buildTime: undefined,
        timelineBtimeSupport: true,
        sandboxSupport: true,
      },
      osInfo: {
        system: 'Linux',
        node: 'node1',
        release: 'release1',
        version: 'version1',
        machine: 'x86_64',
        kernel: 'Linux',
        fqdn: 'foo.bar',
        installDate: new Date(1571789986678),
        libcVer: '10',
        architecture: 'x86_64',
      },
      users: [{
        username: 'foo.bar',
        fullName: 'Foo Bar',
        lastLogon: new Date(1571789996679),
        homedir: '/home/foobar',
        uid: 123,
        gid: 234,
        shell: '/bin/bash',
      }],
      networkInterfaces: [{
        macAddress: 'AA:AB:AC:AD:AE:AF',
        interfaceName: 'lo',
        addresses: [
          {
            addressType: 'IPv4',
            ipAddress: '128.0.0.1',
          },
          {
            addressType: 'IPv6',
            ipAddress: 'F000:0000:0000:0000:0000:0000:0000:0001',
          },
        ],
      }],
      volumes: [{
        name: 'A',
        devicePath: '/foo/bar',
        fileSystemType: 'NTFS',
        bytesPerSector: BigInt('4096'),
        totalSize: BigInt('4096000000'),
        freeSpace: BigInt('409600000'),
        creationTime: new Date(1571789496679),
        unixDetails: {mountPoint: '/', mountOptions: 'readonly'},
        windowsDetails: {
          attributes: ['READONLY'],
          driveLetter: 'D',
          driveType: 'DRIVE_CDROM',
        },
      }],
      cloudInstance: {
        cloudType: CloudInstanceInstanceType.GOOGLE,
        google: {
          hostname: 'hostname',
          instanceId: '123',
          machineType: 'm1',
          projectId: 'p1',
          uniqueId: 'uniq1',
          zone: 'z1',
        },
        amazon: {
          amiId: 'ami1',
          hostname: 'hostname',
          instanceId: 'instance1',
          instanceType: 'm1',
          publicHostname: 'publichostname',
        },
      },
      hardwareInfo: {
        serialNumber: 'serialNumber1',
        systemManufacturer: 'systemManufacturer1',
        systemProductName: 'systemProductName1',
        systemUuid: 'systemUuid1',
        systemSkuNumber: 'systemSkuNumber1',
        systemFamily: 'systemFamily1',
        biosVendor: 'biosVendor1',
        biosVersion: 'biosVersion1',
        biosReleaseDate: 'biosReleaseDate1',
        biosRomSize: 'biosRomSize1',
        biosRevision: 'biosRevision1',
        systemAssettag: 'systemAssettag1',
      },
      memorySize: BigInt(1234),
      firstSeenAt: new Date(1571789996678),
      lastSeenAt: new Date(1571789996679),
      lastBootedAt: new Date(1571789996680),
      lastClock: new Date(1571789996681),
      labels: [
        {name: 'a', owner: 'ao'},
        {name: 'b', owner: 'bo'},
      ],
      age: new Date(1571789996678),
      sourceFlowId: 'f123',
    });
    expect(translateClient(apiClient)).toEqual(client);
  });

  it('converts optional client fields correctly', () => {
    const apiClient: ApiClient = {
      clientId: 'C.1234',
      labels: [],
    };
    const client: Client = newClient({
      clientId: 'C.1234',
      fleetspeakEnabled: false,
      knowledgeBase: {},
      agentInfo: {
        clientName: undefined,
        clientBinaryName: undefined,
        clientDescription: undefined,
        clientVersion: undefined,
        buildTime: undefined,
        revision: undefined,
        sandboxSupport: undefined,
        timelineBtimeSupport: undefined,
      },
      osInfo: {
        system: undefined,
        node: undefined,
        release: undefined,
        version: undefined,
        machine: undefined,
        kernel: undefined,
        fqdn: undefined,
        installDate: undefined,
        libcVer: undefined,
        architecture: undefined,
      },
      users: [],
      networkInterfaces: [],
      volumes: [],
      cloudInstance: undefined,
      hardwareInfo: undefined,
      memorySize: undefined,
      firstSeenAt: undefined,
      lastSeenAt: undefined,
      lastBootedAt: undefined,
      lastClock: undefined,
      labels: [],
      age: undefined,
      sourceFlowId: undefined,
    });
    expect(client).toEqual(translateClient(apiClient));
  });
});
