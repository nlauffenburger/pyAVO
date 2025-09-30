function summed_output=sum_interval_output(transect_col,biomass_col)
%sum_interval_output.m
%
%usage: sum_interval_output(transect_col,biomass_col)
%
%used to read excel file of database output in transect intervals, and sums for
%each transect.  example: transect number is in the 3rd column of the file; weight
%in mt is the 8th column.  you give the col number when you
%call the function
%
%changed code 11/30/04 to use transect indices from file, not create a vector
%from min and max of indices.  ensures that if there are skipped transects this will
%be preserved in the output
%
%changed code 12/01/05 so that this function doesn't read the file in,
%rather works on a Matlab variables in the workspace (I commented out
%following lines and changed code to refer to input variables):
%read in excel file
%data=xlsread(x);
%
%Example
% >> test_transect=[1,1,1,2,2,3,0,0,0]'
% 
% test_transect =
% 
%      1
%      1
%      1
%      2
%      2
%      3
%      0
%      0
%      0
% 
% >> test_biomass=[10,20,30,5,2,4,6,7,2]'
% 
% test_biomass =
% 
%     10
%     20
%     30
%      5
%      2
%      4
%      6
%      7
%      2
% 
% >> sum_interval_output(test_transect,test_biomass)
% 
% ans =
% 
%      0    15
%      1    60
%      2     7
%      3     4

%find size of input data matrix
[numrows,numcols]=size(transect_col);

%sort by transect number if necessary
temp=sortrows([transect_col biomass_col],1);
transect_col=temp(:,1);
biomass_col=temp(:,2);

% %find transect numbers
% start=min(data(1:numrows,transect_col));
% theend=max(data(1:numrows,transect_col));
transect_numbers_list=unique(transect_col);

%pre-allocate memory for output
summed_output=zeros(length(transect_numbers_list),2);

%initialize a counter variable
counter=1;

%sum biomass (col biomass_col of data) for each transect (each unique number in col transect_col column of data variable)
for i=1:length(transect_numbers_list)
       
    transect_number=find(transect_col==transect_numbers_list(i));
    transect_total=sum(biomass_col(transect_number));
    summed_output(counter,:)=[transect_numbers_list(i) transect_total];
    
    counter=counter+1;
    
end
