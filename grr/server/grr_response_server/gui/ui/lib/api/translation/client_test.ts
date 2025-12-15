import {initTestEnvironment} from '../../../testing';
import {
  Client,
  ClientInformation,
  ClientSnapshot,
  Filesystem,
  NetworkInterface,
  StartupInfo,
  StorageVolume,
  User,
} from '../../models/client';
import {newClient} from '../../models/model_test_util';
import {
  ApiClient,
  ClientInformation as ApiClientInformation,
  ClientSnapshot as ApiClientSnapshot,
  Filesystem as ApiFilesystem,
  Interface as ApiNetworkInterface,
  StartupInfo as ApiStartupInfo,
  User as ApiUser,
  Volume as ApiVolume,
  ClientLabel,
  CloudInstanceInstanceType,
  NetworkAddressFamily,
  WindowsVolumeWindowsDriveTypeEnum,
  WindowsVolumeWindowsVolumeAttributeEnum,
} from '../api_interfaces';
import {
  translateClient,
  translateClientInformation,
  translateClientLabel,
  translateClientSnapshot,
  translateClientStartupInfo,
  translateFilesystem,
  translateNetworkInterface,
  translateStorageVolume,
  translateUser,
} from './client';

initTestEnvironment();

describe('Client API Translation', () => {
  describe('translateClientInformation', () => {
    it('converts all client information fields correctly', () => {
      const apiClientInfo: ApiClientInformation = {
        clientName: 'foo',
        clientBinaryName: 'bar',
        clientDescription: 'awesome client',
        clientVersion: 100,
        buildTime: '2025-03-25T12:34:56.789Z',
        revision: '9',
        timelineBtimeSupport: true,
        sandboxSupport: true,
      };
      const clientInfo: ClientInformation = {
        clientName: 'foo',
        clientVersion: 100,
        revision: BigInt(9),
        buildTime: new Date('2025-03-25T12:34:56.789Z'),
        clientBinaryName: 'bar',
        clientDescription: 'awesome client',
        timelineBtimeSupport: true,
        sandboxSupport: true,
      };
      expect(translateClientInformation(apiClientInfo)).toEqual(clientInfo);
    });

    it('converts optional client information fields correctly', () => {
      const apiClientInfo: ApiClientInformation = {
        clientName: undefined,
        clientBinaryName: undefined,
        clientDescription: undefined,
        clientVersion: undefined,
        buildTime: undefined,
        revision: undefined,
        timelineBtimeSupport: undefined,
        sandboxSupport: undefined,
      };
      const clientInfo: ClientInformation = {
        clientName: undefined,
        clientVersion: undefined,
        revision: undefined,
        buildTime: undefined,
        clientBinaryName: undefined,
        clientDescription: undefined,
        timelineBtimeSupport: undefined,
        sandboxSupport: undefined,
      };
      expect(translateClientInformation(apiClientInfo)).toEqual(clientInfo);
    });
  });

  describe('translateClientStartupInfo', () => {
    it('converts all startup info fields correctly', () => {
      const apiStartupInfo: ApiStartupInfo = {
        clientInfo: {},
        bootTime: '157178999678000',
        interrogateRequested: true,
        timestamp: '157178999678000',
      };
      const startupInfo: StartupInfo = {
        clientInfo: {
          clientName: undefined,
          clientVersion: undefined,
          revision: undefined,
          buildTime: undefined,
          clientBinaryName: undefined,
          clientDescription: undefined,
          timelineBtimeSupport: undefined,
          sandboxSupport: undefined,
        },
        bootTime: new Date(157178999678),
        interrogateRequested: true,
        timestamp: new Date(157178999678),
      };
      expect(translateClientStartupInfo(apiStartupInfo)).toEqual(startupInfo);
    });

    it('converts optional startup info fields correctly', () => {
      const apiStartupInfo: ApiStartupInfo = {
        clientInfo: {},
      };
      const startupInfo: StartupInfo = {
        clientInfo: {
          clientName: undefined,
          clientVersion: undefined,
          revision: undefined,
          buildTime: undefined,
          clientBinaryName: undefined,
          clientDescription: undefined,
          timelineBtimeSupport: undefined,
          sandboxSupport: undefined,
        },
        bootTime: undefined,
        interrogateRequested: undefined,
        timestamp: undefined,
      };
      expect(translateClientStartupInfo(apiStartupInfo)).toEqual(startupInfo);
    });
  });

  describe('translateNetworkInterface', () => {
    it('converts all network interface fields correctly', () => {
      const apiNetworkInterface: ApiNetworkInterface = {
        macAddress: 'qqusra6v',
        ifname: 'lo',
        addresses: [
          {addressType: NetworkAddressFamily.INET, packedBytes: 'gAAAAQ=='},
          {
            addressType: NetworkAddressFamily.INET6,
            packedBytes: '8AAAAAAAAAAAAAAAAAAAAQ==',
          },
        ],
      };
      const networkInterface: NetworkInterface = {
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
      };
      expect(translateNetworkInterface(apiNetworkInterface)).toEqual(
        networkInterface,
      );
    });

    it('converts optional network interface fields correctly', () => {
      const apiNetworkInterface: ApiNetworkInterface = {};
      const networkInterface: NetworkInterface = {
        macAddress: undefined,
        interfaceName: undefined,
        addresses: [],
      };
      expect(translateNetworkInterface(apiNetworkInterface)).toEqual(
        networkInterface,
      );
    });
  });

  describe('translateStorageVolume', () => {
    it('converts all storage volume fields correctly', () => {
      const apiVolume: ApiVolume = {
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
      };
      const storageVolume: StorageVolume = {
        name: 'A',
        devicePath: '/foo/bar',
        fileSystemType: 'NTFS',
        bytesPerSector: BigInt(4096),
        totalSize: BigInt(4096000000),
        freeSpace: BigInt(409600000),
        creationTime: new Date(1571789496679),
        unixDetails: {mountPoint: '/', mountOptions: 'readonly'},
        windowsDetails: {
          attributes: ['READONLY'],
          driveLetter: 'D',
          driveType: 'DRIVE_CDROM',
        },
      };
      expect(translateStorageVolume(apiVolume)).toEqual(storageVolume);
    });

    it('converts optional storage volume fields correctly', () => {
      const apiVolume: ApiVolume = {};
      const storageVolume: StorageVolume = {
        name: undefined,
        devicePath: undefined,
        fileSystemType: undefined,
        bytesPerSector: undefined,
        totalSize: undefined,
        freeSpace: undefined,
        creationTime: undefined,
        unixDetails: undefined,
        windowsDetails: undefined,
      };
      expect(translateStorageVolume(apiVolume)).toEqual(storageVolume);
    });
  });

  describe('translateFilesystem', () => {
    it('converts all filesystem fields correctly', () => {
      const apiFilesystem: ApiFilesystem = {
        device: 'device1',
        mountPoint: 'mountPoint1',
        type: 'type1',
        label: 'label1',
      };
      const filesystem: Filesystem = {
        device: 'device1',
        mountPoint: 'mountPoint1',
        type: 'type1',
        label: 'label1',
      };
      expect(translateFilesystem(apiFilesystem)).toEqual(filesystem);
    });

    it('converts optional filesystem fields correctly', () => {
      const apiFilesystem: ApiFilesystem = {};
      const filesystem: Filesystem = {
        device: undefined,
        mountPoint: undefined,
        type: undefined,
        label: undefined,
      };
      expect(translateFilesystem(apiFilesystem)).toEqual(filesystem);
    });
  });

  describe('translateClientSnapshot', () => {
    it('converts all client snapshot fields correctly', () => {
      const apiClientSnapshot: ApiClientSnapshot = {
        clientId: 'C.1234',
        filesystems: [
          {
            device: 'device1',
            mountPoint: 'mountPoint1',
            type: 'type1',
            label: 'label1',
          },
        ],
        osRelease: 'osRelease1',
        osVersion: 'osVersion1',
        arch: 'arch1',
        installTime: '1571789996678000',
        knowledgeBase: {
          fqdn: 'foo.bar',
          os: 'Linux',
          osMajorVersion: 10,
          osMinorVersion: 12,
          users: [
            {
              username: 'foo.bar',
              fullName: 'Foo Bar',
              lastLogon: '1571789996679000',
              homedir: '/home/foobar',
              uid: 123,
              gid: 234,
              shell: '/bin/bash',
            },
          ],
        },
        kernel: 'kernel1',
        volumes: [
          {
            name: 'A',
            devicePath: '/foo/bar',
            fileSystemType: 'NTFS',
            bytesPerSector: '4096',
            actualAvailableAllocationUnits: '100000',
            sectorsPerAllocationUnit: '1',
            totalAllocationUnits: '1000000',
          },
        ],
        interfaces: [
          {
            macAddress: 'qqusra6v',
            ifname: 'lo',
            addresses: [
              {addressType: NetworkAddressFamily.INET, packedBytes: 'gAAAAQ=='},
              {
                addressType: NetworkAddressFamily.INET6,
                packedBytes: '8AAAAAAAAAAAAAAAAAAAAQ==',
              },
            ],
          },
        ],
        hardwareInfo: {
          serialNumber: 'serialNumber1',
          systemManufacturer: 'manufacturer1',
          systemProductName: 'productName1',
          systemUuid: 'uuid1',
          systemSkuNumber: 'skuNumber1',
          systemFamily: 'family1',
          biosVendor: 'biosVendor1',
          biosVersion: 'biosVersion1',
          biosReleaseDate: 'biosReleaseDate1',
          biosRomSize: 'romSize1',
          biosRevision: 'revision1',
          systemAssettag: 'assettag1',
        },
        memorySize: '1234',
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
        startupInfo: {
          clientInfo: {
            clientName: 'foo',
            clientVersion: 100,
            buildTime: '2025-03-25T12:34:56.789Z',
            clientBinaryName: 'client-binary-name',
            clientDescription: 'client-description',
            revision: '9',
            timelineBtimeSupport: true,
            sandboxSupport: true,
          },
          bootTime: '1571789996678000',
          interrogateRequested: true,
          timestamp: '1571789996679000',
        },
        metadata: {
          sourceFlowId: '1234567890',
        },
        timestamp: '1571789996679000',
      };
      const clientSnapshot: ClientSnapshot = {
        clientId: 'C.1234',
        sourceFlowId: '1234567890',
        filesystems: [
          {
            device: 'device1',
            mountPoint: 'mountPoint1',
            type: 'type1',
            label: 'label1',
          },
        ],
        osRelease: 'osRelease1',
        osVersion: 'osVersion1',
        arch: 'arch1',
        installTime: new Date(1571789996678),
        knowledgeBase: {
          fqdn: 'foo.bar',
          os: 'Linux',
          osMajorVersion: 10,
          osMinorVersion: 12,
          users: [
            {
              username: 'foo.bar',
              fullName: 'Foo Bar',
              lastLogon: '1571789996679000',
              homedir: '/home/foobar',
              uid: 123,
              gid: 234,
              shell: '/bin/bash',
            },
          ],
        },
        users: [
          {
            username: 'foo.bar',
            fullName: 'Foo Bar',
            lastLogon: new Date(1571789996679),
            homedir: '/home/foobar',
            uid: 123,
            gid: 234,
            shell: '/bin/bash',
          },
        ],
        kernel: 'kernel1',
        volumes: [
          {
            name: 'A',
            devicePath: '/foo/bar',
            fileSystemType: 'NTFS',
            bytesPerSector: BigInt(4096),
            totalSize: BigInt(4096000000),
            freeSpace: BigInt(409600000),
            creationTime: undefined,
            unixDetails: undefined,
            windowsDetails: undefined,
          },
        ],
        networkInterfaces: [
          {
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
          },
        ],
        hardwareInfo: {
          serialNumber: 'serialNumber1',
          systemManufacturer: 'manufacturer1',
          systemProductName: 'productName1',
          systemUuid: 'uuid1',
          systemSkuNumber: 'skuNumber1',
          systemFamily: 'family1',
          biosVendor: 'biosVendor1',
          biosVersion: 'biosVersion1',
          biosReleaseDate: 'biosReleaseDate1',
          biosRomSize: 'romSize1',
          biosRevision: 'revision1',
          systemAssettag: 'assettag1',
        },
        memorySize: BigInt(1234),
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
        startupInfo: {
          clientInfo: {
            clientName: 'foo',
            clientVersion: 100,
            buildTime: new Date('2025-03-25T12:34:56.789Z'),
            clientBinaryName: 'client-binary-name',
            clientDescription: 'client-description',
            revision: BigInt(9),
            timelineBtimeSupport: true,
            sandboxSupport: true,
          },
          bootTime: new Date(1571789996678),
          interrogateRequested: true,
          timestamp: new Date(1571789996679),
        },
        timestamp: new Date(1571789996679),
      };
      expect(translateClientSnapshot(apiClientSnapshot)).toEqual(
        clientSnapshot,
      );
    });

    it('converts optional client snapshot fields correctly', () => {
      const apiClientSnapshot: ApiClientSnapshot = {
        clientId: 'C.12345678',
      };
      const clientSnapshot: ClientSnapshot = {
        clientId: 'C.12345678',
        sourceFlowId: '',
        filesystems: [],
        osRelease: undefined,
        osVersion: undefined,
        arch: undefined,
        installTime: undefined,
        knowledgeBase: {},
        users: [],
        kernel: undefined,
        volumes: [],
        networkInterfaces: [],
        hardwareInfo: undefined,
        memorySize: undefined,
        cloudInstance: undefined,
        startupInfo: {
          clientInfo: {
            clientName: undefined,
            clientVersion: undefined,
            buildTime: undefined,
            clientBinaryName: undefined,
            clientDescription: undefined,
            revision: undefined,
            timelineBtimeSupport: undefined,
            sandboxSupport: undefined,
          },
          bootTime: undefined,
          interrogateRequested: undefined,
          timestamp: undefined,
        },
        timestamp: undefined,
      };
      expect(translateClientSnapshot(apiClientSnapshot)).toEqual(
        clientSnapshot,
      );
    });
  });

  describe('translateClient', () => {
    it('converts all client fields correctly', () => {
      const apiClient: ApiClient = {
        clientId: 'C.1234',
        knowledgeBase: {
          fqdn: 'foo.bar',
          os: 'Linux',
          osMajorVersion: 10,
          osMinorVersion: 12,
          users: [
            {
              username: 'foo.bar',
              fullName: 'Foo Bar',
              lastLogon: '1571789996679000',
              homedir: '/home/foobar',
              uid: 123,
              gid: 234,
              shell: '/bin/bash',
            },
          ],
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
        rrgVersion: '1.2.3',
        volumes: [
          {
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
              attributesList: [
                WindowsVolumeWindowsVolumeAttributeEnum.READONLY,
              ],
              driveLetter: 'D',
              driveType: WindowsVolumeWindowsDriveTypeEnum.DRIVE_CDROM,
            },
          },
        ],
        interfaces: [
          {
            macAddress: 'qqusra6v',
            ifname: 'lo',
            addresses: [
              {addressType: NetworkAddressFamily.INET, packedBytes: 'gAAAAQ=='},
              {
                addressType: NetworkAddressFamily.INET6,
                packedBytes: '8AAAAAAAAAAAAAAAAAAAAQ==',
              },
            ],
          },
          {
            macAddress: 'qqusra6v',
            addresses: [],
          },
          {
            ifname: 'lo',
          },
        ],
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
        knowledgeBase: {
          fqdn: 'foo.bar',
          os: 'Linux',
          osMajorVersion: 10,
          osMinorVersion: 12,
          users: [
            {
              username: 'foo.bar',
              fullName: 'Foo Bar',
              lastLogon: '1571789996679000',
              homedir: '/home/foobar',
              uid: 123,
              gid: 234,
              shell: '/bin/bash',
            },
          ],
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
        rrgVersion: '1.2.3',
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
        // TODO: Remove outer users field.
        users: [
          {
            username: 'foo.bar',
            fullName: 'Foo Bar',
            lastLogon: new Date(1571789996679),
            homedir: '/home/foobar',
            uid: 123,
            gid: 234,
            shell: '/bin/bash',
          },
        ],
        networkInterfaces: [
          {
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
          },
          {
            macAddress: 'AA:AB:AC:AD:AE:AF',
            interfaceName: undefined,
            addresses: [],
          },
          {
            macAddress: undefined,
            interfaceName: 'lo',
            addresses: [],
          },
        ],
        volumes: [
          {
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
          },
        ],
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
        rrgVersion: undefined,
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

  describe('translateUser', () => {
    it('converts all user fields correctly', () => {
      const apiUser: ApiUser = {
        username: 'foo.bar',
        fullName: 'Foo Bar',
        lastLogon: '1571789996679000',
        homedir: '/home/foobar',
        uid: 123,
        gid: 234,
        shell: '/bin/bash',
      };
      const user: User = {
        username: 'foo.bar',
        fullName: 'Foo Bar',
        lastLogon: new Date(1571789996679),
        homedir: '/home/foobar',
        uid: 123,
        gid: 234,
        shell: '/bin/bash',
      };
      expect(translateUser(apiUser)).toEqual(user);
    });
  });

  describe('translateClientLabel', () => {
    it('returns the name of the client label', () => {
      const apiLabel: ClientLabel = {
        name: 'foo',
        owner: 'bar',
      };
      expect(translateClientLabel(apiLabel)).toEqual('foo');
    });
  });
});
