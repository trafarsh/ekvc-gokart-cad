"""STEP writers (single named+coloured parts and instanced assemblies) via OCAF/XCAF."""
from __future__ import annotations

from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TDF import TDF_Label
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool


def _new_doc():
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("XmlXCAF"))
    app.InitDocument(doc)
    return doc


def _color(rgb):
    return Quantity_Color(float(rgb[0]), float(rgb[1]), float(rgb[2]), Quantity_TOC_RGB)


def _write(doc, path, name):
    Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    Interface_Static.SetCVal_s("write.step.product.name", name)
    w = STEPCAFControl_Writer()
    w.SetColorMode(True)
    w.SetNameMode(True)
    w.Transfer(doc, STEPControl_AsIs)
    st = w.Write(str(path))
    if st != IFSelect_RetDone:
        raise RuntimeError(f"STEP write failed: {path}")


def write_part(shape, path, name, rgb=(0.7, 0.7, 0.7)):
    """Write one part (single or multi-body) as a STEP *part* (not an assembly)."""
    doc = _new_doc()
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    lab = st.AddShape(shape.wrapped, False)
    TDataStd_Name.Set_s(lab, TCollection_ExtendedString(name))
    ct.SetColor(lab, _color(rgb), XCAFDoc_ColorType.XCAFDoc_ColorSurf)
    _write(doc, path, name)


def write_assembly(instances, path, name):
    """instances: list of dict(part_id, shape, rgb, loc: cq.Location, inst_name).
    Shapes with the same part_id are written once and instanced."""
    doc = _new_doc()
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    top = st.NewShape()
    TDataStd_Name.Set_s(top, TCollection_ExtendedString(name))
    protos = {}
    for inst in instances:
        pid = inst["part_id"]
        if pid not in protos:
            lab = st.AddShape(inst["shape"].wrapped, False)
            TDataStd_Name.Set_s(lab, TCollection_ExtendedString(pid))
            ct.SetColor(lab, _color(inst["rgb"]), XCAFDoc_ColorType.XCAFDoc_ColorSurf)
            protos[pid] = lab
        comp = st.AddComponent(top, protos[pid], inst["loc"].wrapped)
        TDataStd_Name.Set_s(comp, TCollection_ExtendedString(inst.get("inst_name", pid)))
    st.UpdateAssemblies()
    _write(doc, path, name)
