"""Offscreen VTK renderer for quick PNG previews of shapes/assemblies."""
from __future__ import annotations

import vtk


def _polydata(shape, tol=0.6, ang=0.4):
    verts, tris = shape.tessellate(tol, ang)
    pts = vtk.vtkPoints()
    for p in verts:
        pts.InsertNextPoint(p.x, p.y, p.z)
    cells = vtk.vtkCellArray()
    for t in tris:
        cells.InsertNextCell(3)
        for i in t:
            cells.InsertCellPoint(i)
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(cells)
    n = vtk.vtkPolyDataNormals()
    n.SetInputData(pd)
    n.SetFeatureAngle(35)
    n.Update()
    return n.GetOutput()


VIEWS = {
    # name: (direction from target to camera, view-up)
    "iso": ((1.0, 0.75, 1.15), (0, 1, 0)),
    "iso_rear": ((-1.0, 0.8, -1.1), (0, 1, 0)),
    "top": ((0.0, 1.0, 0.0001), (1, 0, 0)),
    "side": ((0.0, 0.0001, 1.0), (0, 1, 0)),
    "side_left": ((0.0, 0.0001, -1.0), (0, 1, 0)),
    "front": ((1.0, 0.0001, 0.0), (0, 1, 0)),
}


def render(items, path, view="iso", size=(1400, 1000), bg=(1, 1, 1), edges=False, tol=0.8, zoom=1.0,
           title=None):
    """items: list of (shape, (r,g,b)) in 0..1."""
    ren = vtk.vtkRenderer()
    ren.SetBackground(*bg)
    for shape, color in items:
        try:
            pd = _polydata(shape, tol)
        except Exception:
            continue
        m = vtk.vtkPolyDataMapper()
        m.SetInputData(pd)
        a = vtk.vtkActor()
        a.SetMapper(m)
        a.GetProperty().SetColor(*color)
        a.GetProperty().SetAmbient(0.18)
        a.GetProperty().SetDiffuse(0.85)
        a.GetProperty().SetSpecular(0.25)
        a.GetProperty().SetSpecularPower(20)
        if edges:
            a.GetProperty().EdgeVisibilityOn()
            a.GetProperty().SetEdgeColor(0.2, 0.2, 0.2)
        ren.AddActor(a)
    kit = vtk.vtkLightKit()
    kit.SetKeyLightIntensity(0.95)
    kit.AddLightsToRenderer(ren)
    cam = ren.GetActiveCamera()
    d, up = VIEWS[view]
    ren.ResetCamera()
    fp = cam.GetFocalPoint()
    dist = cam.GetDistance()
    cam.SetPosition(fp[0] + d[0] * dist, fp[1] + d[1] * dist, fp[2] + d[2] * dist)
    cam.SetViewUp(*up)
    if view in ("top", "side", "side_left", "front"):
        cam.ParallelProjectionOn()
    ren.ResetCamera()
    cam.Zoom(zoom)
    if title:
        txt = vtk.vtkTextActor()
        txt.SetInput(title)
        tp = txt.GetTextProperty()
        tp.SetFontSize(26)
        tp.SetColor(0.1, 0.1, 0.1)
        tp.BoldOn()
        txt.SetDisplayPosition(20, size[1] - 50)
        ren.AddActor2D(txt)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(*size)
    win.SetMultiSamples(4)
    win.AddRenderer(ren)
    win.Render()
    f = vtk.vtkWindowToImageFilter()
    f.SetInput(win)
    f.Update()
    w = vtk.vtkPNGWriter()
    w.SetFileName(str(path))
    w.SetInputConnection(f.GetOutputPort())
    w.Write()
    return path
