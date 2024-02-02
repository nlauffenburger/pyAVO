function EBS_commercial_transect=EBS_commercial_createtransects(cellnames,celldata,scaling_factor)
%takes input of a vector of cell names and vector of data for those cells and adds into
%transects based on the cell name, e.g. A-01 and B-01 are in transect 1.
%The other input is the scaling factor; if none was used for this set,
%enter 1 as the argument
%
%uses only valid grid cells
%
%usage:  EBS_commercial_transect=EBS_commercial_createtransects(EBS_commercial_cellnames.valid,EBS_commercial_index_cellsummary(:,1),1.1405)
%        EBS_commercial_transect=EBS_commercial_createtransects(textdata(2:end,1),data(:,5),1.0)
%
%if NaN (empty cell) in celldata, for now delete it (treated as zero for summing
%purposes
celldata=celldata(isnan(celldata)~=1); 
cellnames=cellnames(isnan(celldata)~=1); 


%transect numbers to do
disp('For these transect numbers...');
transect_numbers={'01' '02' '03' '04' '05' '06' '07' '08'...
    '09' '10' '11' '12' '13' '14' '15' '16' '17'...
    '18' '19' '20' '21' '22' '23' '24' '25' '26'...
    '27' '28' '29' '30' '31' '32' '33' '34' '35' '36'};

%flip around for index transect ordering
transect_numbers=[fliplr(transect_numbers(1:17)) transect_numbers(18:32)];

%find indices to data for each transect
for m=1:length(transect_numbers)

    for n=1:length(cellnames)
        temp_index=strfind(cellnames{n},transect_numbers{m});
        if isempty(temp_index)==0  %logical 1 where data
            index_transect_data(n,m)=1;
        else
            index_transect_data(n,m)=0;  %logical 0 where no data
        end
    end
    
end

%convert index matrix from double to logical
index_transect_data=logical(index_transect_data);

%find sum, average, std, n for each transect
%assume equal area of blocks so multiplication by area is neglected
for m=1:length(transect_numbers)
    if sum(index_transect_data(:,m))~=0  %where data exist, do math and enter results
        EBS_commercial_transect.sum(m)=...
            sum(celldata(index_transect_data(:,m)));
        EBS_commercial_transect.mean(m)=...
            mean(celldata(index_transect_data(:,m)));
        EBS_commercial_transect.std(m)=...
            std(celldata(index_transect_data(:,m)));
        EBS_commercial_transect.numblocks(m)=...
            length(celldata(index_transect_data(:,m)));
        EBS_commercial_transect.transect(m)=str2num(transect_numbers{m});
    else  %where no data, enter NaN
        EBS_commercial_transect.sum(m)=NaN;
        EBS_commercial_transect.mean(m)=NaN;
        EBS_commercial_transect.std(m)=NaN;
        EBS_commercial_transect.numblocks(m)=NaN;
        EBS_commercial_transect.transect(m)=str2num(transect_numbers{m});
    end
end

%massage output?
%multiply by scaling factor used to scale the index for this year
EBS_commercial_transect.sum=EBS_commercial_transect.sum.*scaling_factor;  %this sum should equal the index value
EBS_commercial_transect.mean=EBS_commercial_transect.mean.*scaling_factor;
EBS_commercial_transect.std=EBS_commercial_transect.std.*scaling_factor;


% %plot
% figure
% bar(EBS_commercial_transect.transect,EBS_commercial_transect.sum)
% xlabel('transect')
% ylabel('sum sA')

    