%make_EVfiles.m
%create EV files from a directory of rawfiles using a specified number of
%raw files and a template.  also creates an editable bottom line based on
%multifrequency bottom pick
clear all

%UPDATE THE FOLLOWING
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%datafilepath='\\nmfs.local\akc-race\GF_Acoustic\2021\EBS_2021_AlaskaKnight\tri-wave corrected\subsampled\';
datafilepath='I:\2021\EBS_2021_Vesteraalen\AVO_new\SS_1\';
EVfilepath='G:\AVO\EV files and exports\2021\Vest EV files (nouveau)\SS_1\';
template = 'G:\AVO\EV files and exports\templates\Vest2021_template100521.EV';%ideally, the calibration file should already be in the template
ship = 'Vest'; %choose AKN, Vest, etc (if using this for Vesteraalen, make sure to comment out/ uncomment lines 80-81)
subsample = '01'; %choose 01, 11, etc.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%make a list of the data files in specified directory
files = dir([datafilepath '*.raw']);


%arrange filenames
fname = char(files.name);
howmanyrawfiles=length(fname);
datename = fname(:,7:15);
dates = unique(datename,'rows');





%make an EV file for each line
for i = 1:length(dates)% 
    dateid = cellstr(dates(i,:));
    a=strfind(cellstr(datename),dateid);%puts '1' where linename = lineid
    isOne = cellfun(@(x)isequal(x,1),a);%finds the locations of '1'
    idx=find(isOne);%and indexes the location
    subset_of_rawfiles= fname(idx,:);
    
    %start Echoview    
    EvApp = actxserver('EchoviewCom.EvApplication');  %this creates COM object EvApp
    EvApp.Minimize;  %This invokes the method Minimize for COM object EVApp.  Makes the Echoview window minimized.


    % create new EV file with specified template
    newEVfile=EvApp.NewFile(template);

    %set calibration file if necessary
    % newEVfileset.invoke
    % 	GetCalibrationFileName = string GetCalibrationFileName(handle)
    % 	SetCalibrationFile = bool SetCalibrationFile(handle, string)

    %create Fileset COM object
    newEVfileset=newEVfile.Filesets.FindByName('Primary fileset');
    
    %add data files to that file set
    for d=1:length(idx)
        %invoke(newEVfileset.DataFiles,'Add','F:\Patrick_LSSS\S2010210_PJOHANHJORT_1019\ACOUSTIC_DATA\LSSS\KORONA\2011213-D20110831-T162040-korona.raw');
        invoke(newEVfileset.DataFiles,'Add',[datafilepath subset_of_rawfiles(d,:)]);
    end
    
   
    %save new EV file
    newEVfile.SaveAs([EVfilepath ship '_' dates(i,:) '_SS' subsample '.EV']);
    evfilenamestr=[EVfilepath ship  '_' dates(i,:) '_SS' subsample '.EV'];

    
    %close the EV file and move on to next file...
    EvApp.CloseFile(newEVfile);
    
    %but wait!  reopen file, create editable line, resave, close file
    newEVfile=EvApp.OpenFile(evfilenamestr);  %this is invokes the OpenFile method for COM object EvApp (the server),
                                          %and assigns the result to object EvFile

    %force pre-read of data files using a method
    newEVfile.PreReadDataFiles;
    
    %create (overwite) editable line 0.5m off bottom using mean of all sounder-detected bottom lines
    %newline is a COM object; newline.name produces a string with the line name
    %sdb = newEVfile.Lines.FindByName('Mean of all sounder-detected bottom lines');
    sdb = newEVfile.Lines.FindByName('Primary fileset: line data sounder detected bottom T1');% for Vesteraalen just 38 kHz
    newline= newEVfile.Lines.CreateOffsetLinear(sdb,1,-0.5,1); %arguments are source line handle, multiplier, offset, boolean span gaps
    oldline = newEVfile.Lines.FindByName('0.5 m off bottom line');
    oldline.OverwriteWith(newline);
    
    newEVfile.Save;

    EvApp.CloseFile(newEVfile);

    %close application
    EvApp.Quit;  %semi-colon prevents 'ans = 1' from appearing to the screen
 
end

disp('All done making EV files!')

%clear workspace
disp('clearing workspace')
clear
