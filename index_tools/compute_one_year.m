% compute_one_year.m
% Code designed to specifically handle AVO data.
% It assumes subsamples (1 & 11) are organized into line 1 and 11.

function results = compute_one_year(db,ship_list,survey_list,max_depth,classes,interval_min,time_max,...
                                    min_number_intervals,plot_map_track, plot_nasc_track, save_track_sA, plot_nasc_hist, plot_nasc_grid,output_path)

if plot_map_track
    plot_list = {'k.','r.','g.','b.'};
    
end
grid_list = [];
stations = [];
all_grids = [];
all_stations = [];
L = length(survey_list);
full_lat = [];
full_lon = [];
full_nasc = [];
total_sA = [];
cur_year = floor(survey_list(1)/100);
disp(['Working on year ',num2str(cur_year)])
%% Get integration data
for i=1:L
    cur_ship = ship_list(i);
    cur_survey = survey_list(i);
    data{i} = get_integration_data(db, cur_ship, cur_survey, max_depth);
    
    % Index for the lines with the correct classes, time and number of
    % pings
    indc = strcmp(data{i}.class,classes);
    % We need to add in a an entry for every interval where there isn't
    % pollock (PK1, or the chosen class) as PK1 = 0.  Otherwise, the zero
    % pollock isn't included in the averages.  Sometimes when scrutinizing,
    % we might included near zero pollock all the time and other time we
    % won't.  In the later cases, we don't have the 0s for pollock to bring
    % the average to the correct level.  This needs to be consistent.
    non_class_intervals = unique(data{i}.id(~indc));
    [~,indi,~] = intersect(non_class_intervals,data{i}.id(indc));
    for j=1:length(non_class_intervals)
       if sum(j==indi)==0
           % Double check that this interval hasn't been added already by a
           % different non-main-class
          if sum(non_class_intervals(j) == data{i}.id(indc))==0
              indint = find(data{i}.id==non_class_intervals(j));
              data{i}.id = [data{i}.id; data{i}.id(indint(1))];
              data{i}.grid_id = [data{i}.grid_id; data{i}.grid_id(indint(1))];
              data{i}.line = [data{i}.line; data{i}.line(indint(1))];
              data{i}.start_lat = [data{i}.start_lat; data{i}.start_lat(indint(1))];
              data{i}.start_lon = [data{i}.start_lon; data{i}.start_lon(indint(1))];
              data{i}.end_lat = [data{i}.end_lat; data{i}.end_lat(indint(1))];
              data{i}.end_lon = [data{i}.end_lon; data{i}.end_lon(indint(1))];
              data{i}.start_time = [data{i}.start_time; data{i}.start_time(indint(1))];
              data{i}.end_time = [data{i}.end_time; data{i}.end_time(indint(1))];
              data{i}.length = [data{i}.length; data{i}.length(indint(1))];
              data{i}.mean_speed = [data{i}.mean_speed; data{i}.mean_speed(indint(1))];
              data{i}.mean_ex_below_depth = [data{i}.mean_ex_below_depth; data{i}.mean_ex_below_depth(indint(1))];
              data{i}.num_pings = [data{i}.num_pings; data{i}.num_pings(indint(1))];
              data{i}.class = [data{i}.class; 'PK1'];
              data{i}.nasc = [data{i}.nasc; 0];
              data{i}.station_id = [data{i}.station_id; data{i}.station_id(indint(1))];
              data{i}.shape = [data{i}.shape; data{i}.shape(indint(1))];
          end
       end
    end
    % Now select again for the class of interest
    indc = strcmp(data{i}.class,classes);
    indt = seconds(datetime(data{i}.end_time)-datetime(data{i}.start_time))<time_max ...
                   & data{i}.num_pings>=interval_min;
    inda = indc & indt;
    ind1 = data{i}.line == 1 & inda & data{i}.nasc>0;
    ind11 = data{i}.line == 11 & inda & data{i}.nasc>0;
    
    if plot_map_track
        if i==1
            f = figure;
            f.Position = [100 100 1200 800];
        end
       plot(data{i}.start_lon(ind1),data{i}.start_lat(ind1),plot_list{2*i-1})
       hold on
       plot(data{i}.start_lon(ind11)+.1,data{i}.start_lat(ind11)+.05,plot_list{2*i})
    end
    
    % Generate list of unique grid cell ids to loop through later
    grid_list = unique([grid_list;unique(data{i}.grid_id(inda))]);
    stations = unique([stations;unique(data{i}.station_id(inda))]);
    all_grids = [all_grids;data{i}.grid_id(inda)];
    all_stations = [all_stations;data{i}.station_id(inda)];
    full_lat = [full_lat;data{i}.start_lat(inda)];
    full_lon = [full_lon;data{i}.start_lon(inda)];
    full_nasc = [full_nasc;data{i}.nasc(inda)];
end
if plot_map_track
    title(sprintf('Ship tracks for non-zero pollock intervals AVO year %s',num2str(cur_year)))
    legend(sprintf('ship %s SS 1',num2str(ship_list(1))),sprintf('ship %s SS 11',num2str(ship_list(1))), ...
           sprintf('ship %s SS 1',num2str(ship_list(2))),sprintf('ship %s SS 11',num2str(ship_list(2))))
    set(gca,'xdir','reverse')
    set(gca,'fontsize',18)
    xlabel('Longitude')
    ylabel('Latitude')
    orient portrait
    pngfile=[output_path,sprintf('%s-trackline.png',num2str(cur_year))];
    print('-dpng','-r90',pngfile);
end


%% Gather data for index
% Cycle through each grid cell
full_lon = [];
full_lat = [];
full_nasc = [];
for g=1:length(grid_list)
    cur_grid = grid_list(g);
    s_ind=all_grids==cur_grid;  station_list(g) = unique(all_stations(s_ind));
    if ~strcmp(station_list(g),'')
    % Compute an index for all data combined
        sA = [];
        dd = [];
        sp = [];
        dt = [];
        comp_dd = [];
        for i=1:L
            cur_ind = strcmp(data{i}.class,classes) & data{i}.grid_id==cur_grid ...
                & seconds(datetime(data{i}.end_time)-datetime(data{i}.start_time))<time_max ...
                & data{i}.num_pings>=interval_min;
            sA = [sA; data{i}.nasc(cur_ind)];
            sp = [sp; data{i}.mean_speed(cur_ind)];
            dd = [dd; data{i}.length(cur_ind)];
            temp_dt = datetime(data{i}.end_time(cur_ind),'InputFormat','MM/dd/uuuu hh:mm:ss aa')-datetime(data{i}.start_time(cur_ind),'InputFormat','MM/dd/uuuu hh:mm:ss aa');
            dt = [dt; seconds(temp_dt)];
            comp_dd = [comp_dd; (seconds(temp_dt).*data{i}.mean_speed(cur_ind)./1.94)./1852];

            full_lon = [full_lon; data{i}.start_lon(cur_ind)];
            full_lat = [full_lat; data{i}.start_lat(cur_ind)];
            full_nasc = [full_nasc; data{i}.nasc(cur_ind)];
        end
        if ~isempty(sA)
            grid_sA_weighted_by_dist(g) = sum(sA.*dd)/sum(dd);
            grid_sA(g) = mean(sA);
            total_dist(g) = sum(dd);
            count(g) = length(sA);
            mean_dist_diff(g) = mean(comp_dd-dd);
        end

        % Compute an index for each subsample separately to compare.
        sA1 = [];
        dd1 = [];
        sp1 = [];
        sA11 = [];
        dd11 = [];
        sp11 = [];
        for i=1:L
            cur_ind1 = data{i}.line == 1 & strcmp(data{i}.class,classes) & data{i}.grid_id==cur_grid ...
                & seconds(datetime(data{i}.end_time)-datetime(data{i}.start_time))<time_max ...
                & data{i}.num_pings>=interval_min;
            sA1 = [sA1; data{i}.nasc(cur_ind1)];
            sp1 = [sp1; data{i}.mean_speed(cur_ind1)];
            dd1 = [dd1; data{i}.length(cur_ind1)];

            cur_ind11 = data{i}.line == 11 & strcmp(data{i}.class,classes) & data{i}.grid_id==cur_grid ...
                & seconds(datetime(data{i}.end_time)-datetime(data{i}.start_time))<time_max ...
                & data{i}.num_pings>=interval_min;
            sA11 = [sA11; data{i}.nasc(cur_ind11)];
            sp11 = [sp11; data{i}.mean_speed(cur_ind11)];
            dd11 = [dd11; data{i}.length(cur_ind11)];
        end

        if ~isempty(sA1)
            grid_sA_weighted_by_dist1(g) = sum(sA1.*dd1)/sum(dd1);
            grid_sA1(g) = mean(sA1);
            total_dist1(g) = sum(dd1);
            count1(g) = length(sA1);
        else
            grid_sA_weighted_by_dist1(g) = 0;
            grid_sA1(g) = 0;
            total_dist1(g) = 0;
            count1(g) = 0;
        end
        if ~isempty(sA11)
            grid_sA_weighted_by_dist11(g) = sum(sA11.*dd11)/sum(dd11);
            grid_sA11(g) = mean(sA11);
            total_dist11(g) = sum(dd11);
            count11(g) = length(sA11);
        else
            grid_sA_weighted_by_dist11(g) = 0;
            grid_sA11(g) = 0;
            total_dist11(g) = 0;
            count11(g) = 0;
        end
        grid_percent_diff(g) = (grid_sA1(g)-grid_sA11(g))*100/grid_sA1(g);
    end
end

if save_track_sA
    filename=['sA_tracks_',num2str(cur_year),'.csv'];
    M = [full_lat,full_lon,full_nasc];
    csvwrite([output_path,filename],M)
end

if plot_nasc_track
    f = figure;
    f.Position = [100 100 1200 800];
    load G:\AADP_project\avobase\queries\matlab\ena_grid_cell_definitions.mat
    load 200mbathy
    load EBS_wpoli
    for j=1:length(stations)
        [~, loc]=ismember(stations{j},grid_cell_definitions.block_code);
        if loc>0
            cell_location.lon_center(j,1)=grid_cell_definitions.lon_center(loc);
            cell_location.lat_center(j,1)=grid_cell_definitions.lat_center(loc);
            cell_location.lon_perimeter(j,1)=grid_cell_definitions.lon_perimeter(loc);
            cell_location.lat_perimeter(j,1)=grid_cell_definitions.lat_perimeter(loc);
        end
    end 
    plot_log10INASC(-full_lon,full_lat,full_nasc,3)
    hold on
    for p=1:length(cell_location.lon_center)
        [x,y]=m_ll2xy(cell2mat(cell_location.lon_perimeter(p)),cell2mat(cell_location.lat_perimeter(p)));
        plot(x,y,'k')
    end
    title(sprintf('%s AVO pollock backscatter (38 kHz s_A, m^2 nmi^-^2)',num2str(cur_year)))
    set(gca,'fontsize',18)
    orient portrait
    pngfile=[output_path,sprintf('%s-nasc-map-Spectral.png',num2str(cur_year))];
    print('-dpng','-r90',pngfile);
end

if plot_nasc_hist
    figure;
    subplot(2,1,1)
    hist(grid_sA1,50)
    title(sprintf('%s Distribution of grid cell mean sA',num2str(cur_year)))
    legend('Subsample 1')
    subplot(2,1,2)
    hist(grid_sA11,50)
    legend('Subsample 11')
    xlabel('Grid s_A m^2 nmi^-^2')
    
    set(gca,'fontsize',18)
    orient portrait
    pngfile=[output_path,sprintf('%s-nasc-distribution.png',num2str(cur_year))];
    print('-dpng','-r90',pngfile);
end

if plot_nasc_grid
    f = figure;
    f.Position = [100 100 1200 800];
    load G:\AADP_project\avobase\queries\matlab\ena_grid_cell_definitions.mat
    load 200mbathy
    load EBS_wpoli
    m_proj('Lambert Conformal Conic','longitudes',[-180 -160],'latitudes',[54 63]);
    for u=1:length(selected_output)
        [b_proj,c_proj]=m_ll2xy(selected_output{1,u},selected_output{2,u});
        plot(b_proj,c_proj,'b-')
        hold on
    end
    [coastlon_proj,coastlat_proj]=m_ll2xy(coastlon,coastlat);
    plot(coastlon_proj,coastlat_proj, 'k');
    xlabel('Longitude','FontName','Times New Roman')
    ylabel('Latitude','FontName','Times New Roman')
    load convention_line
    m_plot(convention_line(:,2),convention_line(:,1),'k--')
    m_grid('FontName','Times New Roman');
    for j=1:length(stations)
        [~, loc]=ismember(stations{j},grid_cell_definitions.block_code);
        if loc>0
            cell_location.lon_center(j,1)=grid_cell_definitions.lon_center(loc);
            cell_location.lat_center(j,1)=grid_cell_definitions.lat_center(loc);
            cell_location.lon_perimeter(j,1)=grid_cell_definitions.lon_perimeter(loc);
            cell_location.lat_perimeter(j,1)=grid_cell_definitions.lat_perimeter(loc);
        end
    end 
    colormap(flipud(brewermap([],'Spectral')))
    for p=1:length(cell_location.lon_center)
        [x,y]=m_ll2xy(cell2mat(cell_location.lon_perimeter(p)),cell2mat(cell_location.lat_perimeter(p)));
        plot(x,y,'k')
        hold on
        if ~isempty(stations{p})
            indS = strcmp(stations{p},station_list);
            x_cen = mean(x);
            y_cen = mean(y);
            s = scatter(x_cen,y_cen,[],log10(grid_sA(indS)+1),'filled');
            s.SizeData = 200;
        end
    end
    caxis([1,3.5])
    h = colorbar;
    h.Ticks = [0,1,2,3,4];
    h.TickLabels = [0,10,100,1000,10000];
    title(sprintf('%s AVO mean grid pollock backscatter (38 kHz s_A, m^2 nmi^-^2)',num2str(cur_year)))
    set(gca,'fontsize',18)
    orient portrait
    pngfile=[output_path,sprintf('%s-mean_nasc_grid-Spectral.png',num2str(cur_year))];
    print('-dpng','-r90',pngfile);
end

%% Combined estimates
indA = count>min_number_intervals;
results.mean_sA = mean(grid_sA_weighted_by_dist);
results.total_sigma_bs = sum(grid_sA_weighted_by_dist(~isnan(grid_sA_weighted_by_dist)))*400/(4*pi);
results.total_sigma_bs_unweighted = sum(grid_sA(~isnan(grid_sA)))*400/(4*pi);
temp = grid_sA_weighted_by_dist(indA);
results.total_sigma_bs_min_count_applied = sum(temp(~isnan(temp)))*400/(4*pi);
results.grid_sA = grid_sA;
results.grid_sA_weighted_by_dist = grid_sA_weighted_by_dist;
results.grid_list = grid_list;
results.station_list = station_list;
results.count = count;

% SS1
ind1 = count1>0;
ind1A = count1>min_number_intervals;
results.total_sigma_bs1 = sum(grid_sA_weighted_by_dist1(~isnan(grid_sA_weighted_by_dist1)))*400/(4*pi);
results.mean_sA1 = mean(grid_sA_weighted_by_dist1(ind1));
results.total_sigma_bs_unweighted1 = sum(grid_sA1(~isnan(grid_sA1)))*400/(4*pi);
temp = grid_sA_weighted_by_dist1(indA);
results.total_sigma_bs_min_count_applied1 = sum(temp(~isnan(temp)))*400/(4*pi);
results.grid_sA1 = grid_sA1(ind1);
results.grid_sA_weighted_by_dist1 = grid_sA_weighted_by_dist1;
results.grid_list1 = grid_list(ind1);
results.station_list1 = station_list(ind1);
results.count1 = count1(ind1);

% SS11
ind11 = count11>0;
ind11A = count1>min_number_intervals;
results.total_sigma_bs11 = sum(grid_sA_weighted_by_dist11(~isnan(grid_sA_weighted_by_dist11)))*400/(4*pi);
results.mean_sA11 = mean(grid_sA_weighted_by_dist11(ind11));
results.total_sigma_bs_unweighted11 = sum(grid_sA11(~isnan(grid_sA11)))*400/(4*pi);
temp = grid_sA_weighted_by_dist11(indA);
results.total_sigma_bs_min_count_applied11 = sum(temp(~isnan(temp)))*400/(4*pi);
results.grid_sA_weighted_by_dist11 = grid_sA_weighted_by_dist11;
results.grid_sA11 = grid_sA11(ind11);
results.grid_list11 = grid_list(ind11);
results.station_list11 = station_list(ind11);
results.count11 = count1(ind11);


%% Statistics from the processing:
% Counts of intervals by grid cell have been computed
% Number of intervals rejected from minimum number of pings
% Number of intervals rejected from max interval time
% Both of the previous
results.total_sA1 = [];
results.total_sA11 = [];
for i=1:L
    cl_ind = strcmp(data{i}.class,classes);
    min_ind = data{i}.num_pings<interval_min & cl_ind;
    max_ind = seconds(datetime(data{i}.end_time)-datetime(data{i}.start_time))>time_max & cl_ind;
    both_ind = min_ind | max_ind;
    
    results.total_ints(i) = sum(cl_ind);
    results.number_rej_min_pings(i) = sum(min_ind);
    results.number_rej_max_time(i) = sum(max_ind);
    results.number_rej_total(i) = sum(both_ind);
    
    
    ind = data{i}.line == 1;
    results.total_sA1 = [results.total_sA1; sum(data{i}.nasc(ind))];
    ind = data{i}.line == 11;
    results.total_sA11 = [results.total_sA11; sum(data{i}.nasc(ind))];

end



