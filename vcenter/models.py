from spyne import Application, ServiceBase, \
    Integer, Unicode, AnyXml, ComplexModel, XmlData, XmlAttribute, rpc
from spyne import Iterable

class CustomList(AnyXml):
    __type_name__ = 'CustomList'

class TypeVal(ComplexModel):
    type = XmlAttribute(Unicode)
    value = XmlData(Unicode)

class PropSet(ComplexModel):
    type = Unicode
    all = Unicode
    pathSet = Unicode

class SelectSet(ComplexModel):
    type = Unicode
    path = Unicode

class ObjectSet(ComplexModel):
    skip = Unicode
    obj = TypeVal
    selectSet = SelectSet

class SpecSet(ComplexModel):
    propSet = PropSet
    objectSet = ObjectSet

class Options(ComplexModel):
    maxObjects = Integer
    maxWaitSeconds = Integer

class RetrievePropertiesModel(ComplexModel):
    specSet = SpecSet
    options = Options

class CreateContainerViewModel(ComplexModel):
    type = Unicode
    recursive = Unicode
    container = TypeVal

class CreateFilterModel(ComplexModel):
    _this = TypeVal
    spec = SpecSet
    partialUpdates = Unicode

class Entity(ComplexModel):
    entity = TypeVal
    recursion = Unicode

class Filter(ComplexModel):
    entity = Entity
    type = Iterable(Unicode)

class CreateCollectorForEvents(ComplexModel):
    _this = TypeVal
    filter = Filter

class WaitForUpdatesEx(ComplexModel):
    _this = TypeVal
    version = Unicode
    options = Options
