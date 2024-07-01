%script EV_export_AVO2021_AKN.m
%modified from EV_multi_file_export_onevar_PHR.m
%modified from Taina's script EV_multi_file_export_onevar.m (in turn based 
%on alex_script.m) by PHR, September 2011
%
%updated Sept 15 2021 for use on 2021 data from Alaska Knight. 

%updated Oct 4 2017, changed order of pingstats calculations/calls to
%Echoview COM to work better on giant EV files (with a lot of .raw files),
%we think this was causing delay in Echoview COM object reply to Matlab
%('Error: System call failed.')

%Syntax for COM in Matlab:
%find properties, use get().  explicit syntax is
%get(object,'propertyname'), implicit is object.propertyname (or object.get
%to see all properties)
%
%to see/use methods, use invoke.  explicit syntax is
%invoke(object,'methodname'), implicit is object.methodname (or
%object.invoke to see all methods)
%
%set() works similarly and would be used to set a property value

format compact

%User-definable parameters:------------------------------------------------------------
EVFilePath = 'G:\AVO\EV Files and exports\2021\Vest EV files (nouveau)\SS_1\';  %this is just a string variable; note that paths must end with a slash

ExportFileBase = 'G:\AVO\EV Files and exports\2021\Vest_exports\SS_1\16m_to_3m_off_bottom\';   %this is just a string variable defining output path

%ECSfilename= 'C:\python_code\AVO\export_script\AKN_2019_finalsurvey.ecs';  %set .ecs file (calibration file) to use.  
ECSfilename= 'G:\AVO\EV Files and exports\2021\Vest_exports\Vest_2021_finalsurvey.ecs';  %set .ecs file (calibration file) to use.                                                                                                               %no trailing slash!
                                                                                                               
%note that the names of these 2 variables changed for 2014

Filesetname='Primary fileset';  %verify this in the template you used

%Variable_for_export  = 'Match ping times both filters ';  %sets the variable to export from each file
Variable_for_export  = 'Match ping times both filters 38';  %sets the variable to export from each file

Variable_for_totalpings = 'Primary fileset: Sv raw pings T1';  %sets variable for determining total pings before filtering

Min_integration_threshold= -70;
Max_integration_threshold= 0;
Surface_exclusion_line= '16 m line';
Bottom_exclusion_line= '3 m off bottom line';
Grid_in_m= 10;
EDSU_in_nmi= 0.5;
EDSU_in_min= 16.66;
%---------------------------------------------------------------------------------------



EvApp = actxserver('EchoviewCom.EvApplication');  %this creates COM object EvApp
EvApp.Minimize;  %This invokes the method Minimize for COM object EVApp.  Makes the Echoview window minimized.

%could set calibrations values for raw variables?  maybe a script that
%opens files, sets cal values and data file paths, then saves files
%see Hly_2008_replace_gains.m  

%make a list of the EV files in the above directory
files = dir([EVFilePath '*.ev']);
files.name

% loop -- select each file, open file, find varible to export
for i = 10,11 %i = 1:size(files,1)
    %some settings already made in EV files.  Make sure of the following:
    
    %open file and select variable
    EvFilename = [EVFilePath files(i).name];  %this is just a string, not an object
    EvFile = EvApp.OpenFile(EvFilename);  %this is invokes the OpenFile method for COM object EvApp (the server),
                                          %and assigns the result to object EvFile
   
    EvVar =  EvFile.Variables.FindByName(Variable_for_export);  %this is invokes the FindByName method for COM object EvFile.Variables
                                                                %and assigns the result to object EvVar
    %force pre-read of data files using a method
    EvFile.PreReadDataFiles;  
    
    %find the fileset and use a method to set the .ecs file (calibration file) to use for it
    Evfileset=EvFile.Filesets.FindByName(Filesetname);  %finding it using a method
    calfiletest=Evfileset.SetCalibrationFile(ECSfilename);  %setting this using a method
        %check to see if .ecs file change was successful, if not, print error
        %message to screen
        if calfiletest~=1
            disp('Failed to reset .ecs file')
            disp('EVFilePath files(i).name')
        end


    
    %set thresholds on export variable
    EvVar.Properties.Data.ApplyMinimumThreshold= 1;  %this is an example of implicit syntax for setting the property ApplyMinimumThreshold of COM object
                                                     %EvVar.Properties.Data.  Won't work if a method is required to set the property,
                                                     %or if the property is read-only.
    EvVar.Properties.Data.MinimumThreshold= Min_integration_threshold;
    EvVar.Properties.Data.ApplyMaximumThreshold= 1;
    EvVar.Properties.Data.MaximumThreshold= Max_integration_threshold;

    %set grid settings
    EvVar.Properties.Grid.SetDepthRangeGrid(1,Grid_in_m);  %1 says use a grid (enum, looked up in EV help)
    EvVar.Properties.Grid.SetTimeDistanceGrid(1,EDSU_in_min);  %1 is time in min (enum, looked up in EV help)

    %set exclusion lines
    EvVar.Properties.Analysis.ExcludeAboveLine = Surface_exclusion_line;  %this is working even though it spits gibberish to the screen
                                                         %alternate syntax for setting this property:
                                                         %EvVar.Properties.Analysis.set('ExcludeAboveLine','16m')
    EvVar.Properties.Analysis.ExcludeBelowLine = Bottom_exclusion_line;

    %**export commands

    % create export file name, using path, survey name convention, first 4
    % characters of EV filename, and zone. EV appends database names, e.g.,(analysis)
    % and then export integration all regions by cells
    %ExportFileName = [ExportFileBase, 'v157-s201006-x2-f38','-',files(i).name(1:4),'-','z',num2str(zone),'-','.csv'];
    %Ald2010_003-Svfilt-ABIN.csv
    %disp('export commands are commented out!')
    ExportFileName = [ExportFileBase, files(i).name(1:4), files(i).name(6:14), '_0', files(i).name(end-4:end-3), '-Svfilt-ABIN','.csv'];
    exporttest=EvVar.ExportIntegrationByRegionsByCellsAll(ExportFileName);

    %check to see if export was successful, if not, print error
    %message to screen
    if exporttest~=1
        disp('The system has failed')
        disp('ExportFileName')
    end                                                         

    %close the EV file and move on to next file
    EvApp.CloseFile(EvFile);

    i
end

disp('All done!')


%close application
EvApp.Quit;  %semi-colon prevents 'ans = 1' from appearing to the screen

