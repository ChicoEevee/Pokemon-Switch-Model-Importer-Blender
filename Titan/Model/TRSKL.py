# automatically generated by the FlatBuffers compiler, do not modify

# namespace: Model

import flatbuffers
from flatbuffers.compat import import_numpy
np = import_numpy()

class TRSKL(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAs(cls, buf, offset=0):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = TRSKL()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def GetRootAsTRSKL(cls, buf, offset=0):
        """This method is deprecated. Please switch to GetRootAs."""
        return cls.GetRootAs(buf, offset)
    # TRSKL
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # TRSKL
    def Version(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.Get(flatbuffers.number_types.Uint32Flags, o + self._tab.Pos)
        return 0

    # TRSKL
    def TransformNodes(self, j):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            x = self._tab.Vector(o)
            x += flatbuffers.number_types.UOffsetTFlags.py_type(j) * 4
            x = self._tab.Indirect(x)
            from Titan.Model.TransformNode import TransformNode
            obj = TransformNode()
            obj.Init(self._tab.Bytes, x)
            return obj
        return None

    # TRSKL
    def TransformNodesLength(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            return self._tab.VectorLen(o)
        return 0

    # TRSKL
    def TransformNodesIsNone(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        return o == 0

    # TRSKL
    def Bones(self, j):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(8))
        if o != 0:
            x = self._tab.Vector(o)
            x += flatbuffers.number_types.UOffsetTFlags.py_type(j) * 4
            x = self._tab.Indirect(x)
            from Titan.Model.Bone import Bone
            obj = Bone()
            obj.Init(self._tab.Bytes, x)
            return obj
        return None

    # TRSKL
    def BonesLength(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(8))
        if o != 0:
            return self._tab.VectorLen(o)
        return 0

    # TRSKL
    def BonesIsNone(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(8))
        return o == 0

    # TRSKL
    def Iks(self, j):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(10))
        if o != 0:
            x = self._tab.Vector(o)
            x += flatbuffers.number_types.UOffsetTFlags.py_type(j) * 4
            x = self._tab.Indirect(x)
            from Titan.Model.IKControl import IKControl
            obj = IKControl()
            obj.Init(self._tab.Bytes, x)
            return obj
        return None

    # TRSKL
    def IksLength(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(10))
        if o != 0:
            return self._tab.VectorLen(o)
        return 0

    # TRSKL
    def IksIsNone(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(10))
        return o == 0

    # TRSKL
    def RigOffset(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(12))
        if o != 0:
            return self._tab.Get(flatbuffers.number_types.Uint32Flags, o + self._tab.Pos)
        return 0

def TRSKLStart(builder):
    builder.StartObject(5)

def Start(builder):
    TRSKLStart(builder)

def TRSKLAddVersion(builder, version):
    builder.PrependUint32Slot(0, version, 0)

def AddVersion(builder, version):
    TRSKLAddVersion(builder, version)

def TRSKLAddTransformNodes(builder, transformNodes):
    builder.PrependUOffsetTRelativeSlot(1, flatbuffers.number_types.UOffsetTFlags.py_type(transformNodes), 0)

def AddTransformNodes(builder, transformNodes):
    TRSKLAddTransformNodes(builder, transformNodes)

def TRSKLStartTransformNodesVector(builder, numElems):
    return builder.StartVector(4, numElems, 4)

def StartTransformNodesVector(builder, numElems):
    return TRSKLStartTransformNodesVector(builder, numElems)

def TRSKLAddBones(builder, bones):
    builder.PrependUOffsetTRelativeSlot(2, flatbuffers.number_types.UOffsetTFlags.py_type(bones), 0)

def AddBones(builder, bones):
    TRSKLAddBones(builder, bones)

def TRSKLStartBonesVector(builder, numElems):
    return builder.StartVector(4, numElems, 4)

def StartBonesVector(builder, numElems):
    return TRSKLStartBonesVector(builder, numElems)

def TRSKLAddIks(builder, iks):
    builder.PrependUOffsetTRelativeSlot(3, flatbuffers.number_types.UOffsetTFlags.py_type(iks), 0)

def AddIks(builder, iks):
    TRSKLAddIks(builder, iks)

def TRSKLStartIksVector(builder, numElems):
    return builder.StartVector(4, numElems, 4)

def StartIksVector(builder, numElems):
    return TRSKLStartIksVector(builder, numElems)

def TRSKLAddRigOffset(builder, rigOffset):
    builder.PrependUint32Slot(4, rigOffset, 0)

def AddRigOffset(builder, rigOffset):
    TRSKLAddRigOffset(builder, rigOffset)

def TRSKLEnd(builder):
    return builder.EndObject()

def End(builder):
    return TRSKLEnd(builder)

import Titan.Model.Bone
import Titan.Model.IKControl
import Titan.Model.TransformNode
try:
    from typing import List
except:
    pass

class TRSKLT(object):

    # TRSKLT
    def __init__(self):
        self.version = 0  # type: int
        self.transformNodes = None  # type: List[Titan.Model.TransformNode.TransformNodeT]
        self.bones = None  # type: List[Titan.Model.Bone.BoneT]
        self.iks = None  # type: List[Titan.Model.IKControl.IKControlT]
        self.rigOffset = 0  # type: int

    @classmethod
    def InitFromBuf(cls, buf, pos):
        trskl = TRSKL()
        trskl.Init(buf, pos)
        return cls.InitFromObj(trskl)

    @classmethod
    def InitFromPackedBuf(cls, buf, pos=0):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, pos)
        return cls.InitFromBuf(buf, pos+n)

    @classmethod
    def InitFromObj(cls, trskl):
        x = TRSKLT()
        x._UnPack(trskl)
        return x

    # TRSKLT
    def _UnPack(self, trskl):
        if trskl is None:
            return
        self.version = trskl.Version()
        if not trskl.TransformNodesIsNone():
            self.transformNodes = []
            for i in range(trskl.TransformNodesLength()):
                if trskl.TransformNodes(i) is None:
                    self.transformNodes.append(None)
                else:
                    transformNode_ = Titan.Model.TransformNode.TransformNodeT.InitFromObj(trskl.TransformNodes(i))
                    self.transformNodes.append(transformNode_)
        if not trskl.BonesIsNone():
            self.bones = []
            for i in range(trskl.BonesLength()):
                if trskl.Bones(i) is None:
                    self.bones.append(None)
                else:
                    bone_ = Titan.Model.Bone.BoneT.InitFromObj(trskl.Bones(i))
                    self.bones.append(bone_)
        if not trskl.IksIsNone():
            self.iks = []
            for i in range(trskl.IksLength()):
                if trskl.Iks(i) is None:
                    self.iks.append(None)
                else:
                    iKControl_ = Titan.Model.IKControl.IKControlT.InitFromObj(trskl.Iks(i))
                    self.iks.append(iKControl_)
        self.rigOffset = trskl.RigOffset()

    # TRSKLT
    def Pack(self, builder):
        if self.transformNodes is not None:
            transformNodeslist = []
            for i in range(len(self.transformNodes)):
                transformNodeslist.append(self.transformNodes[i].Pack(builder))
            TRSKLStartTransformNodesVector(builder, len(self.transformNodes))
            for i in reversed(range(len(self.transformNodes))):
                builder.PrependUOffsetTRelative(transformNodeslist[i])
            transformNodes = builder.EndVector()
        if self.bones is not None:
            boneslist = []
            for i in range(len(self.bones)):
                boneslist.append(self.bones[i].Pack(builder))
            TRSKLStartBonesVector(builder, len(self.bones))
            for i in reversed(range(len(self.bones))):
                builder.PrependUOffsetTRelative(boneslist[i])
            bones = builder.EndVector()
        if self.iks is not None:
            ikslist = []
            for i in range(len(self.iks)):
                ikslist.append(self.iks[i].Pack(builder))
            TRSKLStartIksVector(builder, len(self.iks))
            for i in reversed(range(len(self.iks))):
                builder.PrependUOffsetTRelative(ikslist[i])
            iks = builder.EndVector()
        TRSKLStart(builder)
        TRSKLAddVersion(builder, self.version)
        if self.transformNodes is not None:
            TRSKLAddTransformNodes(builder, transformNodes)
        if self.bones is not None:
            TRSKLAddBones(builder, bones)
        if self.iks is not None:
            TRSKLAddIks(builder, iks)
        TRSKLAddRigOffset(builder, self.rigOffset)
        trskl = TRSKLEnd(builder)
        return trskl
