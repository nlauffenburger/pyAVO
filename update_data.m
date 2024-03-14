% Update_data.m
% Run this after generating the index for the current year
% Code to update figures and data from the full AVO (nouveau) time series

AVO_95_CI = [0.1664,0.2471,0.1587,0.2476,0.1733,0.1618,0.1354,0.1088,0.271,0.2261,0.1940,0.1431]*10^(6);

% Path to the time series data mat file and the new year's data folder
data_path = 'G:\AVO\Index results\testing\';
current_year = 2023;


%% Load historic data and new data, append new data and save
save_path = [data_path,num2str(current_year),'\'];
load([data_path,'AVO_data'])
load([save_path,num2str(current_year)])

CGlat_all = [CGlat_all,CGlat];
CGlon_all = [CGlon_all,CGlon];
all_years_all = [all_years_all,all_years];
east_of_170_all = [east_of_170_all, east_of_170];
west_of_170_all = [west_of_170_all, west_of_170];
grid_count11_all = [grid_count11_all, grid_count11];
grid_count1_all = [grid_count1_all, grid_count1];
grid_count_all = [grid_count_all, grid_count];
index_all = [index_all, index];
index_min_applied11_all = [index_min_applied11_all, index_min_applied11];
index_min_applied1_all = [index_min_applied1_all, index_min_applied1];
index_min_applied_all = [index_min_applied_all, index_min_applied];
index_ss11_all = [index_ss11_all, index_ss11];
index_ss1_all = [index_ss1_all, index_ss1];
rej_max_time_all = [rej_max_time_all, rej_max_time];
rej_min_pings_all = [rej_min_pings_all, rej_min_pings];
rej_total_all = [rej_total_all, rej_total];
scaler11_all = [scaler11_all,scaler11];
scaler1_all = [scaler1_all, scaler1];
scaler_all = [scaler_all, scaler];
ship_list_all = [ship_list_all; ship_list];
survey_list_all = [survey_list_all; survey_list];
total_ints_all = [total_ints_all, total_ints];
total_sA11_all = [total_sA11_all, total_sA11];
total_sA1_all = [total_sA1_all, total_sA1];

save([data_path,'AVO_data_through_',num2str(current_year)],'ship_list_all','survey_list_all','all_years_all', ...
             'grid_count_all','grid_count1_all','grid_count11_all', ...
             'scaler_all','scaler1_all','scaler11_all', ...
             'index_all','index_ss1_all','index_ss11_all', ...
             'index_min_applied_all','index_min_applied1_all','index_min_applied11_all', ...
             'rej_min_pings_all','rej_max_time_all','rej_total_all','total_ints_all','total_sA1_all','total_sA11_all', ...
             'CGlon_all','CGlat_all','west_of_170_all','east_of_170_all', ...
             'AVO_95_CI_all')

%% Generate figures for the preliminary report
load([data_path,'AT_data'])

% Figure 1 -- AT time series on the top and AVO time series on the bottom
f = figure;
f.Position = [100 100 1000 2000];
subplot(2,1,1)
plot(AT_years, AT_index, 'ko-', 'markerfacecolor', 'k')
hold on
errorbar(AT_years,AT_index,AT_95_CI,'k')
xlim([min(AT_years),max(all_years)])
ylabel('Million metric tons')
set(gca,'fontsize',24)
set(gca,'FontName','Times New Roman')
ylim([0,5.2])
subplot(2,1,2)
plot(all_years_all,index_all, 'ko-', 'markerfacecolor', 'k')
hold on
plot(all_years_all(end),index_all(end),'mo','markerfacecolor','m','markersize',10)
hold on
errorbar(all_years_all(1:end-1),index_all(1:end-1),AVO_95_CI,'k')
xlim([min(AT_years),max(all_years)])
ylabel('Total backscatter (m^{2})')
set(gca,'fontsize',24)
set(gca,'FontName','Times New Roman')
orient portrait
pngfile=[save_path,'AT-AVO-time-series.png'];
print('-dpng','-r90',pngfile);


% Figure 2 -- Correlation between AVO and AT
[~,ia,ib] = intersect(all_years_all,AT_years);
AT = AT_index(ib);
AVO = index_all(ia);

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
pngfile=[save_path,'AVO-AT-regression.png'];
print('-dpng','-r90',pngfile);

% Figure 3 -- West and East of 170W percent of pollock
E_prop = east_of_170_all*100./(east_of_170_all+west_of_170_all);
W_prop = west_of_170_all*100./(east_of_170_all+west_of_170_all);
figure
subplot(1,2,1)
bar(all_years_all,W_prop);
hold on
bar(all_years_all(end),W_prop(end),'k')
title('West of the Pribilof Islands (170^{o} W)')
ylabel('Percent of pollock backscatter')
set(gca,'fontsize',20)
set(gca,'FontName','Times New Roman')
xticks(all_years_all(1):2:all_years_all(end));
ylim([0,100])
subplot(1,2,2)
bar(all_years_all,E_prop);
hold on
bar(all_years_all(end),E_prop(end),'k')
title('East of the Pribilof Islands (170^{o} W)')
ylim([0,100])
set(gca,'fontsize',20)
set(gca,'FontName','Times New Roman')
xticks(all_years_all(1):2:all_years_all(end));
orient portrait
pngfile=[save_path,'proportion_of_pollock_east_and_west_of_170.png'];
print('-dpng','-r90',pngfile);

% Figure 5 -- Center of gravity
addpath('index_tools')
plot_CGI(CGlon_all,CGlat_all,all_years_all,save_path)
