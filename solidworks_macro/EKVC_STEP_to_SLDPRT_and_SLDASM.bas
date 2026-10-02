Attribute VB_Name = "EKVC_Convert"
'==============================================================================================
' EKVC Season 4 kart generator  ->  SolidWorks native files
'
'   1. Converts every *.step in  output\common\parts  and  output\<STYLE>\parts  into a native
'      *.SLDPRT saved next to it (same file name).
'   2. Builds  output\<STYLE>\<STYLE>.SLDASM  from  output\<STYLE>\placements.csv : every SLDPRT is
'      inserted and positioned with its exact transform, then fixed.
'   3. LIVE STEERING (output\<STYLE>\kinematics.csv): the steering column, wheel, pitman arm, tie rods,
'      knuckles and front hubs/rims/tyres are released and mated so that turning the steering wheel
'      steers the front wheels (drag the steering wheel with the mouse):
'        column + knuckles : revolute (point coincident + point on axis) to the frame
'        tie rods          : ball joint at each rod-end centre
'        wheel, pitman     : locked to the column;  hub, rim, tyre : locked to their knuckle
'        LimitDistance     : stops the column at full lock
'      The joint points/axes are small 3D sketches named KIN_... added to those parts.
'
' HOW TO RUN (SolidWorks 2016 or newer):
'   Tools > Options > System Options > Import:  untick "Enable 3D Interconnect"
'                                              (so STEP opens as a plain imported body)
'   Tools > Macro > New... (save anywhere) > in the VBA editor: File > Import File... > this .bas
'   Run "main".  When asked, paste the full path of the  output  folder of the repository.
'
' Re-running is safe: existing SLDPRT files are skipped unless OVERWRITE = True.
' Already have the assemblies?  Run "live_steering" instead of "main" to add only the steering mates.
'==============================================================================================
Option Explicit

Const OVERWRITE As Boolean = False
Const INCLUDE_REFERENCE_DRIVER As Boolean = True
Const BUILD_ASSEMBLIES As Boolean = True
Const BUILD_LIVE_STEERING As Boolean = True
Const ADD_STEERING_LIMIT As Boolean = True

Const swDocPART As Long = 1
Const swDocASSEMBLY As Long = 2
Const swSaveAsCurrentVersion As Long = 0
Const swSaveAsOptions_Silent As Long = 1
Const swOpenDocOptions_Silent As Long = 1
Const swDefaultTemplateAssembly As Long = 9
Const swMateCOINCIDENT As Long = 0
Const swMateDISTANCE As Long = 5
Const swMateLOCK As Long = 16
Const swMateAlignCLOSEST As Long = 2
Const swAddMateError_NoError As Long = 1
Const swCustomInfoText As Long = 30
Const swCustomPropertyReplaceValue As Long = 2
Const swRebuildActiveDoc As Long = 2
Const LIVE_FLAG As String = "EKVC_LIVE_STEERING"

Dim swApp As Object
Dim logText As String

Sub main()
    Set swApp = Application.SldWorks
    Dim root As String
    root = DefaultRoot()
    root = InputBox("Full path of the repository 'output' folder (contains 'common' and the S01..S10 folders):", _
                    "EKVC kart converter", root)
    If root = "" Then Exit Sub
    If Right(root, 1) = "\" Then root = Left(root, Len(root) - 1)
    If Dir(root & "\common\parts", vbDirectory) = "" Then
        MsgBox "Could not find " & root & "\common\parts", vbCritical
        Exit Sub
    End If

    Dim styles As Collection
    Set styles = StyleFolders(root)
    Dim n As Long
    n = ConvertFolder(root & "\common\parts")
    Dim sname As Variant
    For Each sname In styles
        n = n + ConvertFolder(root & "\" & sname & "\parts")
    Next sname
    LogMsg n & " STEP files converted to SLDPRT"

    If BUILD_ASSEMBLIES Then
        If BUILD_LIVE_STEERING Then
            For Each sname In styles
                EnsureStyleSketches root & "\" & sname, CStr(sname)
            Next sname
        End If
        For Each sname In styles
            BuildAssembly root & "\" & sname, CStr(sname)
        Next sname
    End If
    MsgBox "Done." & vbCrLf & logText, vbInformation, "EKVC kart converter"
End Sub

' Adds only the live-steering mates to assemblies that already exist (run after "main").
Sub live_steering()
    Set swApp = Application.SldWorks
    Dim root As String
    root = InputBox("Full path of the repository 'output' folder (contains 'common' and the S01..S10 folders):", _
                    "EKVC live steering", DefaultRoot())
    If root = "" Then Exit Sub
    If Right(root, 1) = "\" Then root = Left(root, Len(root) - 1)
    Dim styles As Collection, sname As Variant
    Set styles = StyleFolders(root)
    For Each sname In styles
        EnsureStyleSketches root & "\" & sname, CStr(sname)
    Next sname
    For Each sname In styles
        Dim asmPath As String, e As Long, w As Long, am As Object
        asmPath = root & "\" & sname & "\" & sname & ".SLDASM"
        If Dir(asmPath) = "" Then
            LogMsg sname & ": no assembly yet - run main first"
        Else
            Set am = swApp.OpenDoc6(asmPath, swDocASSEMBLY, swOpenDocOptions_Silent, "", e, w)
            If am Is Nothing Then
                LogMsg sname & ": could not open " & asmPath
            Else
                AddLiveSteering am, root & "\" & sname, CStr(sname)
                swApp.CloseAllDocuments True
            End If
        End If
    Next sname
    MsgBox "Done." & vbCrLf & logText, vbInformation, "EKVC live steering"
End Sub

'--------------------------------------------------------------------------------------------
Function DefaultRoot() As String
    On Error Resume Next
    Dim p As String
    p = swApp.GetCurrentMacroPathFolder
    If p <> "" Then
        If Dir(p & "\..\output\common\parts", vbDirectory) <> "" Then
            DefaultRoot = p & "\..\output"
            Exit Function
        End If
    End If
    DefaultRoot = "C:\ekvc-gokart-cad\output"
End Function

Function StyleFolders(root As String) As Collection
    Dim c As New Collection
    Dim d As String
    d = Dir(root & "\S*", vbDirectory)
    Do While d <> ""
        If (GetAttr(root & "\" & d) And vbDirectory) = vbDirectory Then
            If Dir(root & "\" & d & "\placements.csv") <> "" Then c.Add d
        End If
        d = Dir()
    Loop
    Set StyleFolders = c
End Function

Sub LogMsg(s As String)
    logText = logText & s & vbCrLf
    Debug.Print s
End Sub

'--------------------------------------------------------------------------------------------
Function ConvertFolder(folder As String) As Long
    Dim files As New Collection
    Dim f As String
    f = Dir(folder & "\*.step")
    Do While f <> ""
        files.Add f
        f = Dir()
    Loop
    Dim item As Variant, cnt As Long
    For Each item In files
        If ConvertOne(folder & "\" & item) Then cnt = cnt + 1
    Next item
    ConvertFolder = cnt
End Function

Function ConvertOne(stepPath As String) As Boolean
    Dim outPath As String
    outPath = Left(stepPath, Len(stepPath) - 5) & ".SLDPRT"
    If Not OVERWRITE Then
        If Dir(outPath) <> "" Then
            ConvertOne = False
            Exit Function
        End If
    End If
    Dim importData As Object, errs As Long, warns As Long
    Dim model As Object
    On Error Resume Next
    Set importData = swApp.GetImportFileData(stepPath)
    Set model = swApp.LoadFile4(stepPath, "r", importData, errs)
    On Error GoTo 0
    If model Is Nothing Then
        LogMsg "FAILED to import " & stepPath & " (error " & errs & ")"
        ConvertOne = False
        Exit Function
    End If
    Dim ok As Boolean
    ok = model.Extension.SaveAs(outPath, swSaveAsCurrentVersion, swSaveAsOptions_Silent, Nothing, errs, warns)
    If Not ok Then LogMsg "FAILED to save " & outPath & " (error " & errs & ")"
    swApp.CloseDoc model.GetTitle
    ConvertOne = ok
End Function

'--------------------------------------------------------------------------------------------
Sub BuildAssembly(styleDir As String, styleName As String)
    Dim csvPath As String
    csvPath = styleDir & "\placements.csv"
    Dim asmPath As String
    asmPath = styleDir & "\" & styleName & ".SLDASM"
    If Not OVERWRITE Then
        If Dir(asmPath) <> "" Then
            LogMsg styleName & ": assembly exists, skipped"
            Exit Sub
        End If
    End If

    Dim tmpl As String
    tmpl = swApp.GetDocumentTemplate(swDocASSEMBLY, "", 0, 0#, 0#)
    If tmpl = "" Then tmpl = swApp.GetUserPreferenceStringValue(swDefaultTemplateAssembly)
    Dim asmModel As Object
    Set asmModel = swApp.NewDocument(tmpl, 0, 0#, 0#)
    If asmModel Is Nothing Then
        LogMsg styleName & ": could not create a new assembly (check default assembly template)"
        Exit Sub
    End If
    Dim mu As Object
    Set mu = swApp.GetMathUtility

    Dim fnum As Integer, txt As String, cols() As String
    Dim placed As Long, failed As Long, first As Boolean
    first = True
    swApp.DocumentVisible False, swDocPART
    fnum = FreeFile
    Open csvPath For Input As #fnum
    Line Input #fnum, txt      ' header
    Do While Not EOF(fnum)
        Line Input #fnum, txt
        txt = Replace(txt, vbCr, "")
        If Len(Trim(txt)) > 0 Then
            cols = Split(txt, ",")
            ' 0 instance,1 part_number,2 file_stem,3 scope,4 step_relpath,5..13 rotation (X,Y,Z axis images),
            ' 14..16 translation mm, 17 reference_only
            If Trim(cols(17)) = "1" And Not INCLUDE_REFERENCE_DRIVER Then GoTo nextRow
            Dim rel As String, partPath As String
            rel = Replace(cols(4), "/", "\")
            rel = Left(rel, Len(rel) - 5) & ".SLDPRT"
            partPath = styleDir & "\" & rel
            Dim e As Long, w As Long, pm As Object
            Set pm = swApp.OpenDoc6(partPath, swDocPART, swOpenDocOptions_Silent, "", e, w)
            If pm Is Nothing Then
                LogMsg styleName & ": missing " & partPath
                failed = failed + 1
                GoTo nextRow
            End If
            Dim comp As Object
            Set comp = asmModel.AddComponent5(partPath, 0, "", False, "", 0#, 0#, 0#)
            If comp Is Nothing Then
                LogMsg styleName & ": could not insert " & partPath
                failed = failed + 1
                GoTo nextRow
            End If
            Dim xf(15) As Double, k As Integer
            For k = 0 To 8
                xf(k) = CDbl(Val(cols(5 + k)))
            Next k
            xf(9) = CDbl(Val(cols(14))) / 1000#
            xf(10) = CDbl(Val(cols(15))) / 1000#
            xf(11) = CDbl(Val(cols(16))) / 1000#
            xf(12) = 1#
            xf(13) = 0#: xf(14) = 0#: xf(15) = 0#
            Dim vxf As Variant
            vxf = xf
            Dim mt As Object
            Set mt = mu.CreateTransform(vxf)
            Dim done As Boolean
            done = False
            On Error Resume Next
            done = comp.SetTransformAndSolve2(mt)
            If Not done Then
                Err.Clear
                Set comp.Transform2 = mt
                done = (Err.Number = 0)
            End If
            If Not done Then
                Err.Clear
                comp.Transform2 = mt
                done = (Err.Number = 0)
            End If
            On Error GoTo 0
            If Not done Then LogMsg styleName & ": transform not applied to " & cols(0)
            comp.Select4 False, Nothing, False
            asmModel.FixComponent
            asmModel.ClearSelection2 True
            placed = placed + 1
        End If
nextRow:
    Loop
    Close #fnum
    swApp.DocumentVisible True, swDocPART
    asmModel.ViewZoomtofit2
    Dim ok As Boolean
    ok = asmModel.Extension.SaveAs(asmPath, swSaveAsCurrentVersion, swSaveAsOptions_Silent, Nothing, e, w)
    LogMsg styleName & ": " & placed & " components placed, " & failed & " failed, saved=" & ok
    If ok And BUILD_LIVE_STEERING Then AddLiveSteering asmModel, styleDir, styleName
    swApp.CloseAllDocuments True
End Sub

'============================================================================================ live steering
Function ReadLines(path As String) As Collection
    Dim c As New Collection, fnum As Integer, txt As String
    fnum = FreeFile
    Open path For Input As #fnum
    Line Input #fnum, txt      ' header
    Do While Not EOF(fnum)
        Line Input #fnum, txt
        txt = Replace(txt, vbCr, "")
        If Len(Trim(txt)) > 0 Then c.Add txt
    Loop
    Close #fnum
    Set ReadLines = c
End Function

' instance name -> "relative SLDPRT path|tx|ty|tz" (mm) from placements.csv
Function ReadPlacements(styleDir As String) As Collection
    Dim c As New Collection, ln As Variant, cols() As String, rel As String
    For Each ln In ReadLines(styleDir & "\placements.csv")
        cols = Split(ln, ",")
        rel = Replace(cols(4), "/", "\")
        rel = Left(rel, Len(rel) - 5) & ".SLDPRT"
        On Error Resume Next
        c.Add rel & "|" & cols(14) & "|" & cols(15) & "|" & cols(16), cols(0)
        On Error GoTo 0
    Next ln
    Set ReadPlacements = c
End Function

Function PlacementOf(pl As Collection, inst As String) As String
    On Error Resume Next
    PlacementOf = pl(inst)
End Function

Function FileNameOf(path As String) As String
    Dim p As Long
    p = InStrRev(path, "\")
    FileNameOf = UCase(Mid(path, p + 1))
End Function

' Adds the KIN_... 3D sketches (joint points / axes) to the parts listed in kinematics.csv.
Sub EnsureStyleSketches(styleDir As String, styleName As String)
    Dim kin As String
    kin = styleDir & "\kinematics.csv"
    If Dir(kin) = "" Then
        LogMsg styleName & ": no kinematics.csv - live steering skipped"
        Exit Sub
    End If
    Dim pl As Collection, ln As Variant, cols() As String, added As Long, bad As Long
    Set pl = ReadPlacements(styleDir)
    swApp.DocumentVisible True, swDocPART
    For Each ln In ReadLines(kin)
        cols = Split(ln, ",")
        If cols(0) = "SKETCH" Then
            Dim info As String, partPath As String
            info = PlacementOf(pl, cols(1))
            If info = "" Then
                LogMsg styleName & ": kinematics instance not in placements: " & cols(1)
                bad = bad + 1
            Else
                partPath = styleDir & "\" & Split(info, "|")(0)
                Select Case EnsureSketch(partPath, CStr(cols(2)), cols)
                    Case 1: added = added + 1
                    Case -1: bad = bad + 1: LogMsg styleName & ": could not add sketch " & cols(2) & " to " & partPath
                End Select
            End If
        End If
    Next ln
    swApp.CloseAllDocuments True
    LogMsg styleName & ": live-steering sketches added " & added & ", failed " & bad
End Sub

' 1 = added, 0 = already there, -1 = failed
Function EnsureSketch(partPath As String, skName As String, cols() As String) As Integer
    Dim e As Long, w As Long, pm As Object
    Set pm = swApp.OpenDoc6(partPath, swDocPART, swOpenDocOptions_Silent, "", e, w)
    If pm Is Nothing Then
        EnsureSketch = -1
        Exit Function
    End If
    swApp.ActivateDoc3 pm.GetTitle, False, swRebuildActiveDoc, e
    If Not pm.FeatureByName(skName) Is Nothing Then
        EnsureSketch = 0
        Exit Function
    End If
    Dim sm As Object, ent As Object, k As Integer, v(5) As Double
    For k = 0 To 5
        If 4 + k <= UBound(cols) Then v(k) = CDbl(Val(cols(4 + k))) / 1000#
    Next k
    Set sm = pm.SketchManager
    pm.ClearSelection2 True
    sm.Insert3DSketch True
    sm.AddToDB = True
    If cols(3) = "L" Then
        Set ent = sm.CreateLine(v(0), v(1), v(2), v(3), v(4), v(5))
    Else
        Set ent = sm.CreatePoint(v(0), v(1), v(2))
    End If
    sm.AddToDB = False
    If Not ent Is Nothing Then
        On Error Resume Next
        ent.Select4 False, Nothing
        pm.SketchAddConstraints "sgFIXED"
        pm.ClearSelection2 True
        On Error GoTo 0
    End If
    sm.Insert3DSketch True
    If ent Is Nothing Then
        EnsureSketch = -1
        Exit Function
    End If
    Dim f As Object
    Set f = pm.FeatureByPositionReverse(0)
    If f Is Nothing Then
        EnsureSketch = -1
        Exit Function
    End If
    f.Name = skName
    pm.Save3 swSaveAsOptions_Silent, e, w
    EnsureSketch = 1
End Function

' Finds the component of an instance by file name + translation (works on any assembly built by this macro).
Function FindComp(asmModel As Object, pl As Collection, inst As String) As Object
    Dim info As String, parts() As String
    info = PlacementOf(pl, inst)
    If info = "" Then Exit Function
    parts = Split(info, "|")
    Dim fn As String, tx As Double, ty As Double, tz As Double
    fn = FileNameOf(parts(0))
    tx = CDbl(Val(parts(1))) / 1000#: ty = CDbl(Val(parts(2))) / 1000#: tz = CDbl(Val(parts(3))) / 1000#
    Dim comps As Variant, i As Long, c As Object, a As Variant
    comps = asmModel.GetComponents(True)
    If IsEmpty(comps) Then Exit Function
    For i = 0 To UBound(comps)
        Set c = comps(i)
        If FileNameOf(c.GetPathName) = fn Then
            a = c.Transform2.ArrayData
            If Abs(a(9) - tx) < 0.0005 And Abs(a(10) - ty) < 0.0005 And Abs(a(11) - tz) < 0.0005 Then
                Set FindComp = c
                Exit Function
            End If
        End If
    Next i
End Function

Function AsmName(asmModel As Object) As String
    Dim t As String
    t = asmModel.GetTitle
    If UCase(Right(t, 7)) = ".SLDASM" Then t = Left(t, Len(t) - 7)
    AsmName = t
End Function

Function SelectEntity(asmModel As Object, comp As Object, skName As String, kind As String, addToSel As Boolean) As Boolean
    Dim nm As String, typ As String, ok As Boolean
    If kind = "L" Then
        nm = "Line1@" & skName & "@" & comp.Name2 & "@" & AsmName(asmModel): typ = "EXTSKETCHSEGMENT"
    Else
        nm = "Point1@" & skName & "@" & comp.Name2 & "@" & AsmName(asmModel): typ = "EXTSKETCHPOINT"
    End If
    On Error Resume Next
    ok = asmModel.Extension.SelectByID2(nm, typ, 0, 0, 0, addToSel, 1, Nothing, 0)
    If Not ok Then
        ' fallback: the sketch entity of the part, mapped into the assembly
        Err.Clear
        Dim pd As Object, f As Object, sk As Object, ents As Variant, ent As Object, sd As Object
        Set pd = comp.GetModelDoc2
        Set f = pd.FeatureByName(skName)
        Set sk = f.GetSpecificFeature2
        If kind = "L" Then ents = sk.GetSketchSegments Else ents = sk.GetSketchPoints2
        Set ent = comp.GetCorresponding(ents(0))
        Set sd = asmModel.SelectionManager.CreateSelectData
        sd.Mark = 1
        ok = ent.Select4(addToSel, sd)
        If Err.Number <> 0 Then ok = False
    End If
    On Error GoTo 0
    SelectEntity = ok
End Function

Function AddMateNow(asmModel As Object, mtype As Long, d As Double, dHi As Double, dLo As Double, errS As Long) As Object
    Dim m As Object
    On Error Resume Next
    Set m = asmModel.AddMate5(mtype, swMateAlignCLOSEST, False, d, dHi, dLo, 1#, 1#, 0#, 0#, 0#, False, False, 0, errS)
    If Err.Number <> 0 Then
        Err.Clear
        Set m = asmModel.AddMate3(mtype, swMateAlignCLOSEST, False, d, dHi, dLo, 1#, 1#, 0#, 0#, 0#, False, errS)
    End If
    On Error GoTo 0
    asmModel.ClearSelection2 True
    Set AddMateNow = m
End Function

Sub AddLiveSteering(asmModel As Object, styleDir As String, styleName As String)
    Dim kin As String
    kin = styleDir & "\kinematics.csv"
    If Dir(kin) = "" Then Exit Sub
    Dim cpm As Object, flagVal As String, resolved As String, wasRes As Boolean
    On Error Resume Next
    Set cpm = asmModel.Extension.CustomPropertyManager("")
    cpm.Get5 LIVE_FLAG, False, flagVal, resolved, wasRes
    On Error GoTo 0
    If flagVal = "1" Then
        LogMsg styleName & ": live steering already present"
        Exit Sub
    End If
    asmModel.ResolveAllLightWeightComponents False
    Dim pl As Collection, ln As Variant, cols() As String
    Set pl = ReadPlacements(styleDir)
    Dim okN As Long, badN As Long, c1 As Object, c2 As Object, m As Object, errS As Long
    For Each ln In ReadLines(kin)
        cols = Split(ln, ",")
        Set m = Nothing
        errS = 0
        Select Case cols(0)
        Case "FLOAT"
            Set c1 = FindComp(asmModel, pl, cols(1))
            If c1 Is Nothing Then
                LogMsg styleName & ": component not found: " & cols(1): badN = badN + 1
            Else
                asmModel.ClearSelection2 True
                c1.Select4 False, Nothing, False
                asmModel.UnfixComponent
                asmModel.ClearSelection2 True
            End If
        Case "COINCIDENT", "LIMIT"
            Dim ia As String, sa As String, ka As String, ib As String, sb As String, kb As String
            If cols(0) = "COINCIDENT" Then
                ia = cols(1): sa = cols(2): ka = cols(3): ib = cols(4): sb = cols(5): kb = cols(6)
            Else
                If Not ADD_STEERING_LIMIT Then GoTo nextKin
                ia = cols(1): sa = cols(2): ka = "P": ib = cols(3): sb = cols(4): kb = "P"
            End If
            Set c1 = FindComp(asmModel, pl, ia)
            Set c2 = FindComp(asmModel, pl, ib)
            If c1 Is Nothing Or c2 Is Nothing Then
                LogMsg styleName & ": component not found for " & ln: badN = badN + 1
            Else
                asmModel.ClearSelection2 True
                If SelectEntity(asmModel, c1, sa, ka, False) And SelectEntity(asmModel, c2, sb, kb, True) Then
                    If cols(0) = "COINCIDENT" Then
                        Set m = AddMateNow(asmModel, swMateCOINCIDENT, 0#, 0#, 0#, errS)
                    Else
                        Set m = AddMateNow(asmModel, swMateDISTANCE, CDbl(Val(cols(5))) / 1000#, _
                                           CDbl(Val(cols(7))) / 1000#, CDbl(Val(cols(6))) / 1000#, errS)
                    End If
                Else
                    LogMsg styleName & ": could not select " & sa & " / " & sb
                End If
                asmModel.ClearSelection2 True
                If m Is Nothing Then
                    LogMsg styleName & ": mate failed (" & errS & "): " & ln: badN = badN + 1
                Else
                    okN = okN + 1
                End If
            End If
        Case "LOCK"
            Set c1 = FindComp(asmModel, pl, cols(1))
            Set c2 = FindComp(asmModel, pl, cols(2))
            If c1 Is Nothing Or c2 Is Nothing Then
                LogMsg styleName & ": component not found for " & ln: badN = badN + 1
            Else
                Dim sd As Object
                Set sd = asmModel.SelectionManager.CreateSelectData
                sd.Mark = 1
                asmModel.ClearSelection2 True
                c1.Select4 False, sd, False
                c2.Select4 True, sd, False
                Set m = AddMateNow(asmModel, swMateLOCK, 0#, 0#, 0#, errS)
                If m Is Nothing Then
                    LogMsg styleName & ": lock mate failed (" & errS & "): " & ln: badN = badN + 1
                Else
                    okN = okN + 1
                End If
            End If
        End Select
nextKin:
    Next ln
    asmModel.EditRebuild3
    On Error Resume Next
    If badN = 0 Then cpm.Add3 LIVE_FLAG, swCustomInfoText, "1", swCustomPropertyReplaceValue
    On Error GoTo 0
    Dim e As Long, w As Long
    asmModel.Save3 swSaveAsOptions_Silent, e, w
    LogMsg styleName & ": live steering - " & okN & " mates added, " & badN & " problems" & _
        IIf(badN = 0, " (drag the steering wheel to steer)", "")
End Sub
