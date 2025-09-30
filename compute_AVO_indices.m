% compute_AVO_indices.m 

% Set up
% Add db and index tools packages
clear all; close all; clc;
addpath('G:\matlab\rht_toolbox\database')
addpath('G:\matlab\rht_toolbox\m_map')
addpath('index_tools')

% ouput path for saving plots and data (with a backslash at the end)
output_path = 'G:\Taina\Fishing Vessel data collection\AVO nouveau\index_results\';
output_path = 'C:\temp\AVO\';

% Database credentials:
source = 'afsc';
user = 'avobase2';  
password = 'Pollock#2468';
db = dbOpen(source, user, password,'provider','ODBC');

% Ship and survey lists
ship_list = [134, 454;
                134, 454;
                88, 89;
                89, 454;
                89, 454;
                94, 454;
                94, 454;
                94, 454;
                94, 454;
                94, 454;
                94, 454; 
                94, 454;
                94, 454;
                134, 454];
survey_list = [202405, 202405;
                202505, 202505
                200905, 200905;
                201005, 201005;
                201205, 201205;
                201405, 201405;
                201505, 201505;
                201605, 201605;
                201705, 201705;
                201805, 201805;
                201905, 201905; 
                202105, 202105;
                202205, 202205;
                202305, 202305];


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
% Compute index for individual subsamples or compute combined index
combined_index = false;
% Exclude intervals that have time that is greater than 60 seconds
time_max = 150;
% To look at sensitivity to cells with low sample size, specify a number of
% intervals in a cell below that to remove for an alternative estimate
min_number_intervals = 2;
% Flags for output
plot_map_track = false;
plot_nasc_track = true;
save_track_sA = true;
plot_nasc_hist = false;
plot_nasc_grid = true;
compute_index_for_old_area = false;
compute_transects = false;
compute_cog = false;
%Use nominal EBS area as 2.5*10^5 km^2 = 102043.62 nmi^2
ebs_area = 102043.62;

if compute_index_for_old_area
   [~,old_cells] = xlsread('old_AVO_year_1-4_cells.xlsx'); 
end

if compute_cog
    load ena_grid_cell_definitions
end

for i=1:size(ship_list,1)
    cur_ships = ship_list(i,:);
    cur_surveys = survey_list(i,:);
    all_years(i) = floor(survey_list(i,1)/100);
    % Query data and compute index by cell for one year
    % Make map figures if specified
    results(i) = compute_one_year(db,cur_ships,cur_surveys,max_depth,classes, ...
        interval_min,time_max,min_number_intervals,plot_map_track,plot_nasc_track,save_track_sA,plot_nasc_hist,plot_nasc_grid,output_path);
    
    grid_count(i) = length(results(i).grid_sA);
    grid_count1(i) = length(results(i).grid_sA1);
    grid_count11(i) = length(results(i).grid_sA11);
    % Dimensionless scaler to handle the different number of grid cells per
    % year, though it is a small difference
    scaler(i) = grid_count(i) * 400 / ebs_area;
    scaler1(i) = grid_count1(i) * 400 / ebs_area;
    scaler11(i) = grid_count11(i) * 400 / ebs_area;
    
    index(i) = results(i).total_sigma_bs/scaler(i);
    index_ss1(i) = results(i).total_sigma_bs1/scaler1(i);
    index_ss11(i) = results(i).total_sigma_bs11/scaler11(i);
    index_unweighted(i) = results(i).total_sigma_bs_unweighted/scaler(i);
    index_unweighted_ss1(i) = results(i).total_sigma_bs_unweighted1/scaler1(i);
    index_unweighted_ss11(i) = results(i).total_sigma_bs_unweighted11/scaler11(i);
    index_min_applied(i) = results(i).total_sigma_bs_min_count_applied/scaler(i);
    index_min_applied1(i) = results(i).total_sigma_bs_min_count_applied1/scaler1(i);
    index_min_applied11(i) = results(i).total_sigma_bs_min_count_applied11/scaler11(i);
    rej_min_pings(i) = sum(results(i).number_rej_min_pings);
    rej_max_time(i) = sum(results(i).number_rej_max_time);
    rej_total(i) = sum(results(i).number_rej_total);
    total_ints(i) = sum(results(i).total_ints);
    
    total_sA1(i) = sum(results(i).total_sA1);
    total_sA11(i) = sum(results(i).total_sA11);
    
    if compute_index_for_old_area
        cell_ind = ismember(results(i).station_list,old_cells);
        temp = results(i).grid_sA_weighted_by_dist(cell_ind);
        index_old_cells(i) = sum(temp(~isnan(temp)))*400/(4*pi);
    end
    
    if compute_transects
        transect_data = EBS_commercial_createtransects(results(i).station_list,results(i).grid_sA_weighted_by_dist,1);
        xlswrite([output_path,num2str(all_years(i)),'EVAoutput.xls'],transect_data.transect','Sheet1','A1');
        xlswrite([output_path,num2str(all_years(i)),'EVAoutput.xls'],transect_data.sum','Sheet1','B1');
    end
    
    if compute_cog
        lat = [];
        lon = [];
        sA = [];
        for j=1:length(results(i).station_list)
            ind=find(strcmp(results(i).station_list(j),grid_cell_definitions.block_code));
            if ~isempty(ind)
                lat = [lat,grid_cell_definitions.lat_center(ind(1))];
                lon = [lon,grid_cell_definitions.lon_center(ind(1))];
                sA = [sA,results(i).grid_sA_weighted_by_dist(j)];
            end
        end
        [CGlon(i),CGlat(i)] = center_of_gravity_sA(lon,lat,sA);
        temp = sA(lon < -170);
        west_of_170(i) = sum(temp(~isnan(temp)));
        temp = sA(lon >= -170);
        east_of_170(i) = sum(temp(~isnan(temp)));
    end
    
end


% Make a plot of the indices over time
f = figure;
f.Position = [100 100 1200 800];
plot(all_years(1:end-1),index(1:end-1),'k-o','linewidth',2, 'MarkerFaceColor','k','markersize',8);
hold on
if compute_index_for_old_area
    plot(all_years,index_old_cells,'-.','linewidth',2,'Color',[0.4660 0.6740 0.1880]);
    plot(all_years,index_old_cells,'go', 'MarkerFaceColor',[0.4660 0.6740 0.1880],'markersize',8)
end
plot(all_years(1:end-1),index_ss1(1:end-1),'bo', 'MarkerFaceColor','b','markersize',8)
plot(all_years(1:end-1),index_ss11(1:end-1),'ro', 'MarkerFaceColor','r','markersize',8)
ylabel('Total AVO pollock backscatter')
set(gca,'FontName','Times New Roman')
xlabel('Year')
xticks(all_years(1:end-1))
if compute_index_for_old_area
    legend('All data','Subsample 1', 'Subsample 2','Old AVO index area all new data','location','southeast')
else
    legend('All data','Subsample 1', 'Subsample 2','location','southeast')
end
set(gca,'fontsize',24)
orient portrait
pngfile=[output_path,'index_time_series.png'];
print('-dpng','-r90',pngfile);


f = figure;
f.Position = [100 100 1200 800];
plot(all_years,index,'k-.',all_years,index_unweighted,'k-',all_years,index_min_applied,'k:', ...
    all_years,index_ss1,'b-.',all_years,index_ss1,'b-',all_years,index_min_applied1,'b:', ...
            all_years,index_ss11,'r-.',all_years,index_ss11,'r-',all_years,index_min_applied11,'r:','linewidth',2);
hold on
plot(all_years,index,'ko', 'MarkerFaceColor','k','markersize',10)
plot(all_years,index_unweighted,'ks', 'MarkerFaceColor','k','markersize',10)
plot(all_years,index_min_applied,'kd', 'MarkerFaceColor','k','markersize',10)
plot(all_years,index_ss1,'bo', 'MarkerFaceColor','b','markersize',10)
plot(all_years,index_unweighted_ss1,'bs', 'MarkerFaceColor','b','markersize',10)
plot(all_years,index_min_applied1,'bd', 'MarkerFaceColor','b','markersize',10)
plot(all_years,index_ss11,'ro', 'MarkerFaceColor','r','markersize',10)
plot(all_years,index_unweighted_ss11,'rs', 'MarkerFaceColor','r','markersize',10)
plot(all_years,index_min_applied11,'rd', 'MarkerFaceColor','r','markersize',10)
xticks(all_years)
ylabel('Mean sA in EBS')
xlabel('Year')
legend('Weighted index all data','Unweighted all data','At least 3 intervals/cell all data',...
    'Weighted index SS1','Unweighted SS1','At least 3 intervals/cell SS1',...
    'Weighted index SS11','Unweighted SS11','At least 3 intervals/cell SS11', 'location','northwest')
set(gca,'fontsize',18)
orient portrait
pngfile=[output_path,'index_time_series_multiple_options.png'];
print('-dpng','-r90',pngfile);

% Compute percent east and west of 170 by year
E_prop = east_of_170*100./(east_of_170+west_of_170);
W_prop = west_of_170*100./(east_of_170+west_of_170);
figure
subplot(1,2,1)
bar(all_years,W_prop);
hold on
bar(all_years(end),W_prop(end),'k')
title('West of the Pribilof Islands (170^{o} W)')
ylabel('Percent of pollock backscatter')
set(gca,'fontsize',20)
set(gca,'FontName','Times New Roman')
xticks([all_years(1):2:all_years(end)]);
ylim([0,100])
subplot(1,2,2)
bar(all_years,E_prop);
hold on
bar(all_years(end),E_prop(end),'k')
title('East of the Pribilof Islands (170^{o} W)')
ylim([0,100])
set(gca,'fontsize',20)
set(gca,'FontName','Times New Roman')
xticks([all_years(1):2:all_years(end)]);
orient portrait
pngfile=[output_path,'proportion_of_pollock_east_and_west_of_170.png'];
print('-dpng','-r90',pngfile);

% Print some results to the console
delta_index_unweighted = (index-index_unweighted).*100./index;
delta_index_min_num = (index-index_min_applied).*100./index;
delta_subsample = (index_ss1-index_ss11)*100./mean([index_ss1;index_ss11]);
delta_total_sA = (total_sA1-total_sA11)*100./mean([total_sA1;total_sA11]);
rej_percent = rej_total*100./total_ints;
disp(['Index values for ',num2str(all_years),' is ',num2str(index)])
disp(['Index values using subsample 1 for ',num2str(all_years),' is ',num2str(index_ss1)])
disp(['Index values using subsample 11 for ',num2str(all_years),' is ',num2str(index_ss11)])
disp(['The percent difference between subsamples for ',num2str(all_years),' is ',num2str(delta_subsample)])
disp(['The percent difference between total sA subsamples for ',num2str(all_years),' is ',num2str(delta_total_sA)])
disp(['Index values unweighting by interval for ',num2str(all_years),' is ',num2str(index_unweighted),...
    ' resulting in a change from the index of ',num2str(delta_index_unweighted)])
disp(['Index values restricted to a minimum number of intervals for ',num2str(all_years),' is ',num2str(index_min_applied),...
    ' resulting in a change from the index of ',num2str(delta_index_min_num)])
disp(['The rejection rate based on removing intervals with less than ',num2str(interval_min),...
        ' pings for ',num2str(all_years),' is ',num2str(rej_min_pings)])
disp(['The total intervals rejected based on removing intervals with more than ',num2str(time_max),...
        ' sec for ',num2str(all_years),' is ',num2str(rej_max_time)])
disp(['The total intervals rejected based on removing intervals by both filters ',...
        'for ',num2str(all_years),' is ',num2str(rej_total),' out of ',num2str(total_ints),' total intervals',...
        ' which is a rejection percent of ',num2str(rej_percent)])
disp(['The number of grid cells used for ',num2str(all_years),' is ',num2str(grid_count)])


load AT_data
AVO_95_CI = [0.1664,0.2471,0.1587,0.2476,0.1733,0.1618,0.1354,0.1088,0.271,0.2261,0.1940,0.1431]*10^(6);
[~,ia,ib] = intersect(all_years,AT_years);
years = all_years(ia);
if length(years)>1
    AT = AT_index(ib);
    AVO = index(ia);
    
    figure
    AVO_reg = fitlm(AVO,AT,'Intercept',false);
    AT_pred = predict(AVO_reg,AVO');
    figure
    plot(AVO,AT,'ko','Markersize',10,'markerfacecolor','k')
    hold on
    plot(AVO,AT_pred,'k-')
    text(AVO+30000,AT,num2str(years'),'FontName','Times New Roman', 'FontSize',28, 'Color', [0.25 0.25 0.25])
    %title('AT - AVO regression')
    ylabel('AT survey biomass (million metric tons)')
    xlabel('Total AVO pollock backscatter (m^2)')
    legend(sprintf('R^{2} = %s',num2str(round(AVO_reg.Rsquared.Ordinary,1))),'location','northwest');
    set(gca,'fontsize',28)
    set(gca,'FontName','Times New Roman')
    orient portrait
    pngfile=[output_path,'new-AVO-AT-regression-total-backscatter.png'];
    print('-dpng','-r90',pngfile);
    
    figure
    AVO_reg = fitlm(AVO,AVO_old,'Intercept',false);
    AT_pred = predict(AVO_reg,AVO');
    figure
    plot(AVO,AVO_old,'ko','Markersize',10,'markerfacecolor','k')
    hold on
    plot(AVO,AT_pred,'k-')
    text(AVO+30000,AVO_old,num2str(years'),'FontName','Times New Roman', 'FontSize',28, 'Color', [0.25 0.25 0.25])
    %title('AT - AVO regression')
    ylabel('AVO index (relative to mean 1999-2004)')
    xlabel('Total AVO pollock backscatter (m^2)')
    legend(sprintf('R^{2} = %s',num2str(round(AVO_reg.Rsquared.Ordinary,1))),'location','northwest');
    set(gca,'fontsize',28)
    set(gca,'FontName','Times New Roman')
    orient portrait
    pngfile=[output_path,'AVO_new-AVO_old-regression-total-backscatter.png'];
    print('-dpng','-r90',pngfile);
    
    
    figure
    [~,ic] = intersect(AVO_old_years,years);
    AVO_old = AVO_old_index(ic);
    AVO_old_reg = fitlm(AVO_old,AT,'Intercept',false);
    AT_pred = predict(AVO_old_reg,AVO_old);
    figure
    plot(AVO_old,AT,'ko','Markersize',10,'markerfacecolor','k')
    hold on
    plot(AVO_old,AT_pred,'k-')
    text(AVO_old+0.01,AT,num2str(years'),'FontName','Times New Roman', 'FontSize',28, 'Color', [0.25 0.25 0.25])
    xlim([0.1,1.2])
    ylim([.5,5])
    %plot(AVO_old_reg,'Markersize',20)
    %title('AT - AVO regression')
    ylabel('AT survey biomass (million metric tons)')
    xlabel('AVO index (relative to mean 1999-2004)')
    legend(sprintf('R^{2} = %s',num2str(round(AVO_old_reg.Rsquared.Ordinary,2))),'location','northwest');
    set(gca,'fontsize',28)
    set(gca,'FontName','Times New Roman')
    orient portrait
    pngfile=[output_path,'old-AVO-AT-regression.png'];
    print('-dpng','-r90',pngfile);
    
    figure
    subplot(3,1,1)
    plot(AT_years, AT_index, 'ko-', 'markerfacecolor', 'k')
    xlim([min(AT_years),max(all_years(1:end-1))])
    title('AT survey biomass')
    ylabel('Million metric tons')
    set(gca,'fontsize',14)
    set(gca,'FontName','Times New Roman')
    ylim([0,5.2])
    subplot(3,1,2)
    plot(all_years(1:end-1),index(1:end-1), 'ko-', 'markerfacecolor', 'k')
    xlim([min(AT_years(1:end-1)),max(all_years(1:end-1))])
    title('New AVO')
    ylabel('AVO Index')
    set(gca,'fontsize',14)
    set(gca,'FontName','Times New Roman')
    %ylim([0,550])
    subplot(3,1,3)
    plot(AVO_old_years,AVO_old_index, 'ko-', 'markerfacecolor', 'k')
    xlim([min(AT_years),max(all_years(1:end-1))])
    title('Old AVO')
    ylabel('AVO Index')
    set(gca,'fontsize',14)
    set(gca,'FontName','Times New Roman')
    xlabel('Year')
    ylim([0.2,1.2])
    orient portrait
    pngfile=[output_path,'AT-AVO-time-series_w_old.png'];
    print('-dpng','-r90',pngfile);
    
    figure
    subplot(2,1,1)
    plot(AT_years, AT_index, 'ko-', 'markerfacecolor', 'k')
    hold on
    errorbar(AT_years,AT_index,AT_95_CI,'k')
    xlim([min(AT_years),max(all_years)])
    %title('AT survey biomass')
    ylabel('Million metric tons')
    set(gca,'fontsize',24)
    set(gca,'FontName','Times New Roman')
    ylim([0,5.2])
    subplot(2,1,2)
    plot(all_years,index, 'ko-', 'markerfacecolor', 'k')
    hold on
    plot(all_years(end),index(end),'mo','markerfacecolor','m','markersize',10)
    hold on
    errorbar(all_years,index,AVO_95_CI,'k')
    xlim([min(AT_years),max(all_years)])
    %title('New AVO')
    ylabel('Total backscatter (m^{2})')
    set(gca,'fontsize',24)
    set(gca,'FontName','Times New Roman')
    
    f = figure;
    f.Position = [100 100 3000 4000];
    subplot(3,1,2)
    plot(AT_years(4:end), AT_index(4:end), 'ko-', 'markerfacecolor', 'k')
    hold on
    errorbar(AT_years(4:end),AT_index(4:end),AT_95_CI(4:end),'k')
    xlim([min(all_years),max(all_years)])
    %title('AT survey biomass')
    set(gca,'fontsize',20)
    set(gca,'FontName','Times New Roman')
    ylabel('Million metric tons','Fontsize',17)
    ylim([0,5.2])
    subplot(3,1,1)
    plot(all_years,index, 'ko-', 'markerfacecolor', 'k')
    hold on
    plot(all_years(end),index(end),'mo','markerfacecolor','m','markersize',8)
    hold on
    plot(all_years(end-1),index(end-1),'mo','markerfacecolor','m','markersize',8)
    errorbar(all_years,index,AVO_95_CI,'k')
    xlim([min(all_years),max(all_years)])
    %title('New AVO')
    set(gca,'fontsize',20)
    set(gca,'FontName','Times New Roman')
    ylabel('Total backscatter (m^{2})','Fontsize',17)
    subplot(3,1,3)
    plot(all_years(1:end),index(1:end),'k-o','linewidth',2, 'MarkerFaceColor','k','markersize',5);
    hold on
    plot(all_years(1:end),index_ss1(1:end),'bo', 'MarkerFaceColor','b','markersize',5)
    plot(all_years(1:end),index_ss11(1:end),'ro', 'MarkerFaceColor','r','markersize',5)
    set(gca,'FontName','Times New Roman')
    set(gca,'fontsize',20)
    ylabel('Total backscatter (m^{2})','Fontsize',17)
    xlabel('Year','Fontsize',17)
    xlim([min(all_years),max(all_years)])
    %legend('All data','Subsample 1', 'Subsample 2','location','southeast')
    orient portrait
    
    
    %ylim([0,550])
    orient portrait
    pngfile=[output_path,'AT-AVO-time-series.png'];
    print('-dpng','-r90',pngfile);
    
end

if compute_cog
    plot_CGI(CGlon,CGlat,all_years,output_path)
end


save([output_path,'AVO_data'],'ship_list','survey_list','all_years', ...
             'grid_count','grid_count1','grid_count11', ...
             'scaler','scaler1','scaler11', ...
             'index','index_ss1','index_ss11', ...
             'index_min_applied','index_min_applied1','index_min_applied11', ...
             'rej_min_pings','rej_max_time','rej_total','total_ints','total_sA1','total_sA11', ...
             'CGlon','CGlat','west_of_170','east_of_170', ...
             'AVO_95_CI')
