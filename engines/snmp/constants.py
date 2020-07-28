class ASN1Tags:
    Boolean = 0x01
    Integer = 0x02
    BitString = 0x03
    OctetString = 0x04
    Null = 0x05
    OID = 0x06
    UTF8String = 0x0c
    PrintableString = 0x13
    IA5String = 0x16
    BMPString = 0x1e
    Sequence = 0x30
    IPAddress = 0x40
    Counter32 = 0x41
    Gauge32 = 0x42
    TimeTicks = 0x43
    Opaque = 0x44
    Counter64 = 0x46
    NoSuchObject = 0x80
    NoSuchInstance = 0x81
    EndOfMIB = 0x82
    GetRequest = 0xa0
    GetNextRequest = 0xa1
    GetResponse = 0xa2
    SetRequest = 0xa3
    GetBulkRequest = 0xa5

class ASN1Error:
    NoError = 0x00
    TooBig = 0x01
    NoSuchName = 0x02
    BadValue = 0x03
    ReadOnly = 0x04
    WrongValue = 0x0a

class Opaque:
    Context = 0x80
    ExtensionId = 0x1f
    Tag1 = Context | ExtensionId
    Tag2 = 0x30
    Application = 0x40
    AppFloat = Application | 0x08
    AppDouble = Application | 0x09
    AppInt64 = Application | 0x0a
    AppUInt64 = Application | 0x0b
    Float = Tag2 | AppFloat
    Double = Tag2 | AppDouble
    Int64 = Tag2 | AppInt64
    UInt64 = Tag2 | AppUInt64

class OpaqueLen:
    Float = 7
    Double = 11
    Int64 = 4
    UInt64 = 4

SnmpPdu = (
    'version',
    'community',
    'PDU-type',
    'request-id',
    'error-status',
    'error-index',
    'variable bindings',
)

