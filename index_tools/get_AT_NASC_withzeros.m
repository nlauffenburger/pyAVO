%PHR_getPKNASC_withzeros_2016.m
%coded by PHR 3 Oct 2011.  Checked agains DY1006 multifrequency processing
%of PK* NASC, looked good
%tweaked for 2012 DY1207 data in July 2013 and I think it worked. -PHR
%added code at end to select US EEZ data and sum, September 2013.  Started saving 
%versions of this script for each survey year.  -- PHR

%modified heavily for macebase2 in 2016 -- oct 26, 2016 SCS

%modified to include bottom data pulled from the database and to EXCLUDE
%northern extensions-- oct 31, 2018

outpath='G:\AVO\Index results\2024\';

uname1='macebase2';
pwd1='FishSticks#765';

db =dbOpen('afsc', uname1, pwd1,'provider','ODBC')
% db =dbOpen('AFSCD1', uname1, pwd1)

 
if (db.State < 0)
    error('Unable to connect to haulDatabase.');
end

%this is changed to only grab sA above 3m off btm from MACEBASE2
query=['SELECT MACEBASE2.INTEGRATION_RESULTS.SURVEY,'...
 ' MACEBASE2.INTEGRATION_RESULTS.SHIP,'...
 ' MACEBASE2.INTEGRATION_RESULTS.ZONE,'...
 ' MACEBASE2.INTEGRATION_RESULTS.CLASS,'...
 ' MACEBASE2.INTEGRATION_RESULTS.INTERVAL,'...
'  MACEBASE2.INTERVALS.START_TIME,'...
'  MACEBASE2.INTERVALS.TRANSECT,'... 
'  MACEBASE2.INTERVALS.START_LATITUDE,'...
'  MACEBASE2.INTERVALS.START_LONGITUDE,'...
'  MACEBASE2.INTERVALS.START_VESSEL_LOG,'...
 ' MACEBASE2.INTERVALS.END_VESSEL_LOG,'...
 ' MACEBASE2.INTEGRATION_RESULTS.PRC_NASC'...
' FROM MACEBASE2.INTEGRATION_RESULTS'...
' INNER JOIN MACEBASE2.INTERVALS'...
' ON MACEBASE2.INTERVALS.SURVEY              = MACEBASE2.INTEGRATION_RESULTS.SURVEY'...
' AND MACEBASE2.INTERVALS.SHIP               = MACEBASE2.INTEGRATION_RESULTS.SHIP'...
' AND MACEBASE2.INTERVALS.DATA_SET_ID        = MACEBASE2.INTEGRATION_RESULTS.DATA_SET_ID'...
' AND MACEBASE2.INTERVALS.INTERVAL           = MACEBASE2.INTEGRATION_RESULTS.INTERVAL'...
' WHERE MACEBASE2.INTEGRATION_RESULTS.SURVEY = 202408'...
' AND MACEBASE2.INTEGRATION_RESULTS.SHIP     = 157'...
' AND MACEBASE2.INTEGRATION_RESULTS.DATA_SET_ID = 1'...
' AND MACEBASE2.INTEGRATION_RESULTS.ZONE = 1'...
' AND MACEBASE2.INTERVALS.TRANSECT     < 100']; %added transect > 0 -- this may eliminate unwanted sa (i.e., transect = -99 or null)


water_col_Data = dbQuery(db, query, 'outtype', 'struct');


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%SPECIFIC TO 2018: limit data to Report Numbers 1 & 2 (that is, to omit
%data contained within Report 3, i.e., omit northern transect extensions).
query=['SELECT macebase2.report_bounds.report_number,'...
    ' macebase2.report_bounds.start_vessel_log,'...
    ' macebase2.report_bounds.end_vessel_log'...
' FROM macebase2.report_bounds'...
' WHERE MACEBASE2.report_bounds.survey = 202408'...
' AND macebase2.report_bounds.SHIP = 157'...
' AND macebase2.report_bounds.report_number in (1,2)'...
' AND macebase2.report_bounds.DATA_SET_ID = 1'...
' AND macebase2.report_bounds.ANALYSIS_ID = 1'];

report_data = dbQuery(db, query, 'outtype', 'struct');
dbClose(db);


% %SPECIFIC TO 2018: restrict water column data to those that fall outside of Report #3 
% for i = 1:length(report_data.start_vessel_log)
%     k = find(water_col_Data.start_vessel_log >= report_data.start_vessel_log(i) & water_col_Data.end_vessel_log <= report_data.end_vessel_log(i));
%     water_col_Data.class(k) = [];
%     water_col_Data.interval(k) = [];
%     water_col_Data.start_time(k) = [];
%     water_col_Data.transect(k) = [];
%     water_col_Data.start_latitude(k) = [];
%     water_col_Data.start_longitude(k) = [];
%     water_col_Data.start_vessel_log(k) = [];
%     water_col_Data.end_vessel_log(k) = [];
%     water_col_Data.prc_nasc(k) = [];
% end
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%select data we want
Lat=water_col_Data.start_latitude;
Lon=water_col_Data.start_longitude;
    temp=find(Lon>0);  %take care of positive longitudes and make all neg west
    Lon(temp)=-(360-Lon(temp));  
Cell_sA=water_col_Data.prc_nasc;


%set cell sA for anything that is not == PK1 or PK1_FILTERED to 0
pk = strcmp(water_col_Data.class,'SS1') | strcmp(water_col_Data.class,'SS2') | strcmp(water_col_Data.class,'SS1_FILTERED');
%pk2 = strcmp(water_col_Data.class,'PK1_FILTERED');
%pk_all = pk+pk2;
notPK_index=find(pk==0); %use this if pk1 is the only pollock CLASS
%notPK_index=find(pk_all==0); %use this if more CLASSES than pk1
Cell_sA(notPK_index)=0;



%SCS added this code (9-11-19) to bring in 0.5-3m off btm data, remove zone 3, 
%and append it to the midwater vectors
btm_Data=xlsread('G:\Bering Sea\Below 3m analysis\time series\Interval by year\Results_below_3_m2024.xlsx','Sheet3');
%restrict water column data to those that fall outside of Report #3 
    zone = btm_Data(:,9);
    index =find(zone == 3);
    btm_Data(index,:) = [];
btm_interval = btm_Data(:,1);
btm_sA = btm_Data(:,2);
btm_lat = btm_Data(:,5);
btm_long = btm_Data(:,6);
joint_sA = [Cell_sA;btm_sA];
joint_interval = [water_col_Data.interval;btm_interval];
joint_lat = [water_col_Data.start_latitude;btm_lat];
joint_long = [water_col_Data.start_longitude;btm_long];



%sum PK NASC by interval
EDSU.PKNASC=sum_interval_output(joint_interval,joint_sA);
%find unique VL values. 
[EDSU_interval,EDSU_index,J]=unique(joint_interval);
%note both unique() and sum_interval_output() will sort
%by interval name with this usage.

%just get NASC from output of sum_interval_output.  output of function
%normally has two columns, in this case first column is interval and second is
%NASC
EDSU.PKNASC=EDSU.PKNASC(:,2);

%collect other output
EDSU.Lat=joint_lat(EDSU_index);
EDSU.Lon=joint_long(EDSU_index);

%make a plot
plot_log10INASC(EDSU.Lon,EDSU.Lat,EDSU.PKNASC,2) 
title('2024 AT survey: 38 kHz PK (s_A, m^2 nmi^-^2)')


