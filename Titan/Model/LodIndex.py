# automatically generated by the FlatBuffers compiler, do not modify

# namespace: Model

import flatbuffers
from flatbuffers.compat import import_numpy
np = import_numpy()

class LodIndex(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAs(cls, buf, offset=0):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = LodIndex()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def GetRootAsLodIndex(cls, buf, offset=0):
        """This method is deprecated. Please switch to GetRootAs."""
        return cls.GetRootAs(buf, offset)
    # LodIndex
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # LodIndex
    def Unk0(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.Get(flatbuffers.number_types.Uint32Flags, o + self._tab.Pos)
        return 0

def LodIndexStart(builder):
    builder.StartObject(1)

def Start(builder):
    LodIndexStart(builder)

def LodIndexAddUnk0(builder, unk0):
    builder.PrependUint32Slot(0, unk0, 0)

def AddUnk0(builder, unk0):
    LodIndexAddUnk0(builder, unk0)

def LodIndexEnd(builder):
    return builder.EndObject()

def End(builder):
    return LodIndexEnd(builder)
