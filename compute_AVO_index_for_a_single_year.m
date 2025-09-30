% compute_AVO_index_for_a_single_year.m 
%
% Compute the index for one year
% The two 5% subsample indices are produced for comparison
% A combined 10% subsample is computed as the final index.

% QC figures and data are created:
% - Map of tracks of pollock sA for each subsample
% - Comparisons between subsamples and sensitivity to parameters is output
% - Distribution of grid sAs for each subsample

% Results are created:
% - Map sA along trackline
% - Map of mean sA by grid for 10% combined subsample
% - sA grouped by transect for EVA analysis
% - sA along the trackline for pollock saved as CSV
% - All data saved in mat file


clear all; close all; clc;
% Add db and index tools packages
addpath('G:\matlab\rht_toolbox\database')
addpath('G:\matlab\rht_toolbox\m_map')
addpath('index_tools')

%% Set up:  Generally, we only need to edit this section

% Output path for saving data for the current year (with a backslash at the end)
% A folder with the current year as the name will be made within this
% folder
index_path = 'G:\AVO\Index results\';

% Database credentials:
source = 'afsc';
user = 'avobase2';  
password = 'Pollock#2468';
db = dbOpen(source, user, password,'provider','ODBC');

% Ship and survey list for the current year
ship_list = [134, 454];
survey_list = [202505, 202505];

%% More set up that normally doesn't need to be edited

% Processing parameters:
% Classes for which backscatter combined
classes = {'PK1'};
% Depth limits for analysis, min depth is set in exporter (16 m) 
max_depth = 197;
% In the export step, some intervals are cut into pieces because
% the data were exported based on time (8.33 min) and sometimes it split an interval
% We only want intervals that are complete.
% For now, limit the interval size to be larger than 10 pings
interval_min = 10;
% Exclude intervals that have time that is greater than 60 seconds
time_max = 150;
% To look at sensitivity to cells with low sample size, specify a number of
% intervals in a cell below that to remove for an alternative estimate
min_number_intervals = 2;

% Flags for output
plot_map_track = true;
plot_nasc_track = true;
save_track_sA = true;
plot_nasc_hist = true;
plot_nasc_grid = true;
compute_transects = true;
compute_cog = true;
% Use nominal EBS area as 2.5*10^5 km^2 = 102043.62 nmi^2
ebs_area = 102043.62;

%% Do some final set up: never need
if compute_cog
    load ena_grid_cell_definitions
end
cur_ships = ship_list;
cur_surveys = survey_list;
all_years = floor(survey_list(1)/100);

% Make year folder if needed
output_path = [index_path,num2str(all_years),'\'];

if not(isfolder(output_path))
    mkdir(output_path)
end

%% Compute the index and output results
% Query data and compute index by cell for one year
% Make map figures if specified
results = compute_one_year(db,cur_ships,cur_surveys,max_depth,classes, ...
    interval_min,time_max,min_number_intervals,plot_map_track,plot_nasc_track,save_track_sA,plot_nasc_hist,plot_nasc_grid,output_path);

grid_count = length(results.grid_sA);
grid_count1 = length(results.grid_sA1);
grid_count11 = length(results.grid_sA11);
% Dimensionless scaler to handle the different number of grid cells per
% year, though it is a small difference
scaler = grid_count * 400 / ebs_area;
scaler1 = grid_count1 * 400 / ebs_area;
scaler11 = grid_count11 * 400 / ebs_area;

index = results.total_sigma_bs/scaler;
index_ss1 = results.total_sigma_bs1/scaler1;
index_ss11 = results.total_sigma_bs11/scaler11;
index_min_applied = results.total_sigma_bs_min_count_applied/scaler;
index_min_applied1 = results.total_sigma_bs_min_count_applied1/scaler1;
index_min_applied11 = results.total_sigma_bs_min_count_applied11/scaler11;
rej_min_pings = sum(results.number_rej_min_pings);
rej_max_time = sum(results.number_rej_max_time);
rej_total = sum(results.number_rej_total);
total_ints = sum(results.total_ints);

total_sA1 = sum(results.total_sA1);
total_sA11 = sum(results.total_sA11);

if compute_transects
    transect_data = EBS_commercial_createtransects(results.station_list,results.grid_sA_weighted_by_dist,1);
    xlswrite([output_path,num2str(all_years),'EVAoutput.xls'],transect_data.transect','Sheet1','A1');
    xlswrite([output_path,num2str(all_years),'EVAoutput.xls'],transect_data.sum','Sheet1','B1');
end

if compute_cog
    lat = [];
    lon = [];
    sA = [];
    for j=1:length(results.station_list)
        ind=find(strcmp(results.station_list(j),grid_cell_definitions.block_code));
        if ~isempty(ind)
            lat = [lat,grid_cell_definitions.lat_center(ind(1))];
            lon = [lon,grid_cell_definitions.lon_center(ind(1))];
            sA = [sA,results.grid_sA_weighted_by_dist(j)];
        end
    end
    [CGlon,CGlat] = center_of_gravity_sA(lon,lat,sA);
    temp = sA(lon < -170);
    west_of_170 = sum(temp(~isnan(temp)));
    temp = sA(lon >= -170);
    east_of_170 = sum(temp(~isnan(temp)));
end

delta_index_min_num = (index-index_min_applied).*100./index;
delta_subsample = (index_ss1-index_ss11)*100./mean([index_ss1;index_ss11]);
delta_total_sA = (total_sA1-total_sA11)*100./mean([total_sA1;total_sA11]);
rej_percent = rej_total*100./total_ints;

% Save results in a text file
text_file = [output_path,num2str(all_years),'-statstics.txt'];
writelines(['Index values for ',num2str(all_years),' is ',num2str(index)],text_file,WriteMode='append');
writelines(['Index values using subsample 1 for ',num2str(all_years),' is ',num2str(index_ss1)],text_file,WriteMode='append');
writelines(['Index values using subsample 11 for ',num2str(all_years),' is ',num2str(index_ss11)],text_file,WriteMode='append');
writelines(['The percent difference between subsamples for ',num2str(all_years),' is ',num2str(delta_subsample)],text_file,WriteMode='append');
writelines(['The percent difference between total sA subsamples for ',num2str(all_years),' is ',num2str(delta_total_sA)],text_file,WriteMode='append');
writelines(['Index values restricted to a minimum number of intervals for ',num2str(all_years),' is ',num2str(index_min_applied),...
    ' resulting in a change from the index of ',num2str(delta_index_min_num)],text_file,WriteMode='append');
writelines(['The rejection rate based on removing intervals with less than ',num2str(interval_min),...
        ' pings for ',num2str(all_years),' is ',num2str(rej_min_pings)],text_file,WriteMode='append');
writelines(['The total intervals rejected based on removing intervals with more than ',num2str(time_max),...
        ' sec for ',num2str(all_years),' is ',num2str(rej_max_time)],text_file,WriteMode='append');
writelines(['The total intervals rejected based on removing intervals by both filters ',...
        'for ',num2str(all_years),' is ',num2str(rej_total),' out of ',num2str(total_ints),' total intervals',...
        ' which is a rejection percent of ',num2str(rej_percent)],text_file,WriteMode='append');
writelines(['The number of grid cells used for ',num2str(all_years),' is ',num2str(grid_count)],text_file,WriteMode='append');

save([output_path,num2str(all_years)])