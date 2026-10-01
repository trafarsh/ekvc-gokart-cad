Attribute VB_Name = "EKVC_Convert"
'==============================================================================================
' EKVC Season 4 kart generator  ->  SolidWorks native files
'
'   1. Converts every *.step in  output\common\parts  and  output\<STYLE>\parts  into a native
'      *.SLDPRT saved next to it (same file name).
'   2. Builds  output\<STYLE>\<STYLE>.SLDASM  from  output\<STYLE>\placements.csv : every SLDPRT is
'      inserted and positioned with its exact transform, then fixed.
'
' HOW TO RUN (SolidWorks 2016 or newer):
'   Tools > Options > System Options > Import:  untick "Enable 3D Interconnect"
'                                              (so STEP opens as a plain imported body)
'   Tools > Macro > New... (save anywhere) > in the VBA editor: File > Import File... > this .bas
'   Run "main".  When asked, paste the full path of the  output  folder of the repository.
'
' Re-running is safe: existing SLDPRT files are skipped unless OVERWRITE = True.
'==============================================================================================
Option Explicit

Const OVERWRITE As Boolean = False
Const INCLUDE_REFERENCE_DRIVER As Boolean = True
Const BUILD_ASSEMBLIES As Boolean = True

Const swDocPART As Long = 1
Const swDocASSEMBLY As Long = 2
Const swSaveAsCurrentVersion As Long = 0
Const swSaveAsOptions_Silent As Long = 1
Const swOpenDocOptions_Silent As Long = 1
Const swDefaultTemplateAssembly As Long = 9

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
    Log n & " STEP files converted to SLDPRT"

    If BUILD_ASSEMBLIES Then
        For Each sname In styles
            BuildAssembly root & "\" & sname, CStr(sname)
        Next sname
    End If
    MsgBox "Done." & vbCrLf & logText, vbInformation, "EKVC kart converter"
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

Sub Log(s As String)
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
        Log "FAILED to import " & stepPath & " (error " & errs & ")"
        ConvertOne = False
        Exit Function
    End If
    Dim ok As Boolean
    ok = model.Extension.SaveAs(outPath, swSaveAsCurrentVersion, swSaveAsOptions_Silent, Nothing, errs, warns)
    If Not ok Then Log "FAILED to save " & outPath & " (error " & errs & ")"
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
            Log styleName & ": assembly exists, skipped"
            Exit Sub
        End If
    End If

    Dim tmpl As String
    tmpl = swApp.GetDocumentTemplate(swDocASSEMBLY, "", 0, 0#, 0#)
    If tmpl = "" Then tmpl = swApp.GetUserPreferenceStringValue(swDefaultTemplateAssembly)
    Dim asmModel As Object
    Set asmModel = swApp.NewDocument(tmpl, 0, 0#, 0#)
    If asmModel Is Nothing Then
        Log styleName & ": could not create a new assembly (check default assembly template)"
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
                Log styleName & ": missing " & partPath
                failed = failed + 1
                GoTo nextRow
            End If
            Dim comp As Object
            Set comp = asmModel.AddComponent5(partPath, 0, "", False, "", 0#, 0#, 0#)
            If comp Is Nothing Then
                Log styleName & ": could not insert " & partPath
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
            If Not done Then Log styleName & ": transform not applied to " & cols(0)
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
    Log styleName & ": " & placed & " components placed, " & failed & " failed, saved=" & ok
End Sub
