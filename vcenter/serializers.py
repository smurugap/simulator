import uuid
import copy
from lxml import etree

XSI = "http://www.w3.org/2001/XMLSchema-instance"
class Serializer(object):
    __tag__ = dict()
    __attribute__ = dict()
    def __init__(self, **kwargs):
        for k,v in kwargs.iteritems():
            setattr(self, k, v)

    def serialize(self, parent=None):
        if parent is None:
            parent = etree.Element("returnval", nsmap={'xsi': XSI})
        for k, v in self.__dict__.iteritems():
            if k in self.__tag__:
                self.__tag__[k] = v
        for k,v in self.__tag__.items():
            kwargs = dict()
            if k in self.__attribute__:
                for kattr, vattr in self.__attribute__[k].items():
                    if vattr is not None:
                        kwargs[kattr] = vattr
            tag = etree.SubElement(parent, k, **kwargs)
            if v is None:
                continue
            elif getattr(v, 'serialize', None):
                v.serialize(parent=tag)
            elif isinstance(v, list):
                for elem in v:
                    elem.serialize(parent=tag)
            else:
                tag.text = str(v)
        return parent

    def __getattr__(self, attr):
        if attr in self.__tag__.iterkeys():
            if isinstance(self.__tag__[attr], Serializer):
                obj = self.__tag__[attr].__class__()
                setattr(self, attr, obj)
                return obj
        raise AttributeError('%s object has no attribute %s'%(
            self.__class__.__name__, attr))

    def _setattribute(self, tag, **kwargs):
        if tag in self.__attribute__:
            self.__attribute__ = copy.deepcopy(self.__attribute__)
            for k,v in kwargs.items():
                if k == 'xsi_type':
                    k = '{%s}type'%XSI
                self.__attribute__[tag][k] = v

class AuthResponse(Serializer):
    __tag__ = {
        'userName': "VSPHERE.LOCAL\Administrator",
        'fullName': "Administrator vsphere.local",
        'key': None,
        'loginTime': "2020-09-21T16:45:06.238124Z",
        'lastActiveTime': "2020-09-21T16:45:06.238124Z",
        'locale': 'en',
        'messageLocale': 'en',
        'extensionSession': 'false',
        'ipAddress': '10.87.70.17', #docker_h.my_ip
        'userAgent': 'pyvmomi Python/2.7.5 (Linux; 3.10.0-1062.el7.x86_64; x86_64)',
        'callCount': 0
    }

class SIAbout(Serializer):
    __tag__ = {
        'name': 'VMware vCenter Server',
        'fullName': 'VMware vCenter Server 6.5.0 build-10964411',
        'vendor': 'VMware, Inc.',
        'version': '6.5.0',
        'build': 10964411,
        'localeVersion': 'INTL',
        'localeBuild': '000',
        'osType': 'linux-x64',
        'productLineId': 'vpx',
        'apiType': 'VirtualCenter',
        'apiVersion': 6.5,
        'instanceUuid': str(uuid.uuid4()),
        'licenseProductName': 'VMware VirtualCenter Server',
        'licenseProductVersion': 6.0
    }

class ServiceInstance(Serializer):
    __tag__ = {
        'rootFolder': "group-d1",
        'propertyCollector': 'propertyCollector',
        'viewManager': 'viewManager',
        'about': SIAbout(),
        'setting': 'VpxSettings',
        'userDirectory': 'UserDirectory',
        'sessionManager': 'SessionManager',
        'authorizationManager': 'AuthorizationManager',
        'serviceManager': 'ServiceMgr',
        'perfManager': 'PerfMgr',
        'scheduledTaskManager': 'ScheduledTaskManager',
        'alarmManager': 'AlarmManager',
        'eventManager': 'EventManager',
        'taskManager': 'TaskManager',
        'extensionManager': 'ExtensionManager',
        'customizationSpecManager': 'CustomizationSpecManager',
        'customFieldsManager': 'CustomFieldsManager',
        'diagnosticManager': 'DiagMgr',
        'licenseManager': 'LicenseManager',
        'searchIndex': 'SearchIndex',
        'fileManager': 'FileManager',
        'datastoreNamespaceManager': 'DatastoreNamespaceManager',
        'virtualDiskManager': 'virtualDiskManager',
        'vmProvisioningChecker': 'ProvChecker',
        'vmCompatibilityChecker': 'CompatChecker',
        'ovfManager': 'OvfManager',
        'ipPoolManager': 'IpPoolManager',
        'dvSwitchManager': 'DVSManager',
        'hostProfileManager': 'HostProfileManager',
        'clusterProfileManager': 'ClusterProfileManager',
        'complianceManager': 'MoComplianceManager',
        'localizationManager': 'LocalizationManager',
        'storageResourceManager': 'StorageResourceManager',
        'guestOperationsManager': 'guestOperationsManager',
        'overheadMemoryManager': 'OverheadMemoryManager',
        'certificateManager': 'certificateManager',
        'ioFilterManager': 'IoFilterManager',
        'vStorageObjectManager': 'VStorageObjectManager',
        'hostSpecManager': 'HostSpecificationManager',
        'cryptoManager': 'CryptoManager',
        'healthUpdateManager': 'HealthUpdateManager',
        'failoverClusterConfigurator': 'FailoverClusterConfigurator',
        'failoverClusterManager': 'FailoverClusterManager'
    }
    __attribute__ = {
        'rootFolder': {'type': "Folder"},
        'propertyCollector': {'type': 'PropertyCollector'},
        'viewManager': {'type': 'ViewManager'},
        'setting': {'type': 'OptionManager'},
        'userDirectory': {'type': 'UserDirectory'},
        'sessionManager': {'type': 'SessionManager'},
        'authorizationManager': {'type': 'AuthorizationManager'},
        'serviceManager': {'type': 'ServiceManager'},
        'perfManager': {'type': 'PerformanceManager'},
        'scheduledTaskManager': {'type': 'ScheduledTaskManager'},
        'alarmManager': {'type': 'AlarmManager'},
        'eventManager': {'type': 'EventManager'},
        'taskManager': {'type': 'TaskManager'},
        'extensionManager': {'type': 'ExtensionManager'},
        'customizationSpecManager': {'type': 'CustomizationSpecManager'},
        'customFieldsManager': {'type': 'CustomFieldsManager'},
        'diagnosticManager': {'type': 'DiagnosticManager'},
        'licenseManager': {'type': 'LicenseManager'},
        'searchIndex': {'type': 'SearchIndex'},
        'fileManager': {'type': 'FileManager'},
        'datastoreNamespaceManager': {'type': 'DatastoreNamespaceManager'},
        'virtualDiskManager': {'type': 'VirtualDiskManager'},
        'vmProvisioningChecker': {'type': 'VirtualMachineProvisioningChecker'},
        'vmCompatibilityChecker': {'type': 'VirtualMachineCompatibilityChecker'},
        'ovfManager': {'type': 'OvfManager'},
        'ipPoolManager': {'type': 'IpPoolManager'},
        'dvSwitchManager': {'type': 'DistributedVirtualSwitchManager'},
        'hostProfileManager': {'type': 'HostProfileManager'},
        'clusterProfileManager': {'type': 'ClusterProfileManager'},
        'complianceManager': {'type': 'ProfileComplianceManager'},
        'localizationManager': {'type': 'LocalizationManager'},
        'storageResourceManager': {'type': 'StorageResourceManager'},
        'guestOperationsManager': {'type': 'GuestOperationsManager'},
        'overheadMemoryManager': {'type': 'OverheadMemoryManager'},
        'certificateManager': {'type': 'CertificateManager'},
        'ioFilterManager': {'type': 'IoFilterManager'},
        'vStorageObjectManager': {'type': 'VcenterVStorageObjectManager'},
        'hostSpecManager': {'type': 'HostSpecificationManager'},
        'cryptoManager': {'type': 'CryptoManagerKmip'},
        'healthUpdateManager': {'type': 'HealthUpdateManager'},
        'failoverClusterConfigurator': {'type': 'FailoverClusterConfigurator'},
        'failoverClusterManager': {'type': 'FailoverClusterManager'}
    }

class ManagedObject(Serializer):
    __tag__ = {
        'ManagedObjectReference': None
    }
    __attribute__ = {
        'ManagedObjectReference': {'{%s}type'%XSI: 'ManagedObjectReference', 'type': None}
    }

class PropertySet(Serializer):
    __tag__ = {
        'name': None,
        'val': None
    }
    __attribute__ = {
        'val': {'{%s}type'%XSI: None, 'type': None}
    }

class PropertySetList(Serializer):
    __tag__ = {
        'propSet': PropertySet()
    }

class Objects(Serializer):
    __tag__ = {
        'obj': None,
        'propSet': PropertySet()
    }
    __attribute__ = {
        'obj': {'type': None},
    }

class RetrievePropertiesEx(Serializer):
    __tag__ = {
        'objects': Objects(),
    }

class RetrieveProperties(Serializer):
    __tag__ = {
        'obj': None,
    }
    __attribute__ = {
        'obj': {'type': None},
    }

class HostConfigManager(Serializer):
    __tag__ = {'cpuScheduler': None,
               'datastoreSystem': None,
               'memoryManager': None,
               'storageSystem': None,
               'networkSystem': None,
               'vmotionSystem': None,
               'virtualNicManager': None,
               'serviceSystem': None,
               'firewallSystem': None,
               'advancedOption': None,
               'diagnosticSystem': None,
               'autoStartManager': None,
               'snmpSystem': None,
               'dateTimeSystem': None,
               'patchManager': None,
               'imageConfigManager': None,
               'firmwareSystem': None,
               'healthStatusSystem': None,
               'pciPassthruSystem': None,
               'kernelModuleSystem': None,
               'authenticationManager': None,
               'powerSystem': None,
               'cacheConfigurationManager': None,
               'esxAgentHostManager': None,
               'iscsiManager': None,
               'vFlashManager': None,
               'vsanSystem': None,
               'messageBusProxy': None,
               'userDirectory': None,
               'accountManager': None,
               'hostAccessManager': None,
               'graphicsManager': None,
               'vsanInternalSystem': None,
               'certificateManager': None
              }

    __attribute__ = {'cpuScheduler': {'type': "HostCpuSchedulerSystem"},
                     'datastoreSystem': {'type': "HostDatastoreSystem"},
                     'memoryManager': {'type': "HostMemorySystem"},
                     'storageSystem': {'type': "HostStorageSystem"},
                     'networkSystem': {'type': "HostNetworkSystem"},
                     'vmotionSystem': {'type': "HostVMotionSystem"},
                     'virtualNicManager': {'type': "HostVirtualNicManager"},
                     'serviceSystem': {'type': "HostServiceSystem"},
                     'firewallSystem': {'type': "HostFirewallSystem"},
                     'advancedOption': {'type': "OptionManager"},
                     'diagnosticSystem': {'type': "HostDiagnosticSystem"},
                     'autoStartManager': {'type': "HostAutoStartManager"},
                     'snmpSystem': {'type': "HostSnmpSystem"},
                     'dateTimeSystem': {'type': "HostDateTimeSystem"},
                     'patchManager': {'type': "HostPatchManager"},
                     'imageConfigManager': {'type': "HostImageConfigManager"},
                     'firmwareSystem': {'type': "HostFirmwareSystem"},
                     'healthStatusSystem': {'type': "HostHealthStatusSystem"},
                     'pciPassthruSystem': {'type': "HostPciPassthruSystem"},
                     'kernelModuleSystem': {'type': "HostKernelModuleSystem"},
                     'authenticationManager': {'type': "HostAuthenticationManager"},
                     'powerSystem': {'type': "HostPowerSystem"},
                     'cacheConfigurationManager': {'type': "HostCacheConfigurationManager"},
                     'esxAgentHostManager': {'type': "HostEsxAgentHostManager"},
                     'iscsiManager': {'type': "IscsiManager"},
                     'vFlashManager': {'type': "HostVFlashManager"},
                     'vsanSystem': {'type': "HostVsanSystem"},
                     'messageBusProxy': {'type': "MessageBusProxy"},
                     'userDirectory': {'type': "UserDirectory"},
                     'accountManager': {'type': "HostLocalAccountManager"},
                     'hostAccessManager': {'type': "HostAccessManager"},
                     'graphicsManager': {'type': "HostGraphicsManager"},
                     'vsanInternalSystem': {'type': "HostVsanInternalSystem"},
                     'certificateManager': {'type': "HostCertificateManager"}
                    }

class LLDP(Serializer):
    __tag__ = {'chassisId': '10:0e:7e:ab:9c:00',
               'portId': None,
               'timeToLive': 103}

class ParameterInfo(Serializer):
    __tag__ = {'key': None, 'value': None}
    __attribute__ = {'value': {'{%s}type'%XSI: None}}

class Parameter(Serializer):
    __tag__ = {'parameter': ParameterInfo()}

class NetworkHint(Serializer):
    __tag__ = {
        'device': None,
        'lldpInfo': LLDP()
    }
