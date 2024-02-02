function plot_CGI(CGlon,CGlat,all_years,output_path)

%*****set up figure window with a map projection
f1=figure; 
f1.Position = [100 100 1200 800];
m_proj('Albers Equal-Area Conic','longitudes',[-176 -170],'latitudes',[57.5 60]);

title('title','FontName','Times New Roman')

load 100mbathy.mat
for u=1:length(selected_output)
    [b_proj,c_proj]=m_ll2xy(selected_output{1,u},selected_output{2,u});
    plot(b_proj,c_proj,'Color',[0.5 0.5 0.5],'LineStyle','-')
    hold on
end
set(gca,'FontName','Times New Roman')
set(gca,'FontSize',24)
%plot 200m bathymetry contour
%load('C:\Program Files\MATLAB\R2007a\work\coast\AK_bathy\50mbathy.mat')
load 200mbathy.mat
for u=1:length(selected_output)
    [b_proj,c_proj]=m_ll2xy(selected_output{1,u},selected_output{2,u});
    plot(b_proj,c_proj,'Color',[0.5 0.5 0.5],'LineStyle','-')
    hold on
end
set(gca,'FontName','Times New Roman')
set(gca,'FontSize',24)
%format figure window
set(f1,'Color','w');  
m_grid('FontName','Times New Roman');
m_grid('FontSize',24)
%load and plot coastline data in m_plot window
load EBS_nopoli
[coastlon_proj,coastlat_proj]=m_ll2xy(coastlon,coastlat);
plot(coastlon_proj,coastlat_proj, 'k');
xlabel('Longitude','FontName','Times New Roman')
ylabel('Latitude','FontName','Times New Roman')

%plot convention line if use EBS_nopoli above
load convention_line
m_plot(convention_line(:,2),convention_line(:,1),'k--')

% CGI_ATsurvey=[
% 2006	-172.6156 58.7201 105390 324.6384
% 2007	-174.3140 59.0790 90886 301.4730
% 2008	-173.9995 58.9269 73963 271.9613
% 2009	-172.6827 58.2200 69326 263.2987
% 2010	-175.2373 59.5717 62362 249.7233
% 2012    -173.5880 59.2498 107720 328.2146
% 2014    -170.4699 58.1423 124130	352.3219
% 2016    -171.0219 58.1678 115180    339.3856
% 2018    -171.4704 58.5087 113180    336.4161    
% 2022    -172.8874 58.5449 121666 348.8072
% ];

CGI_ATsurvey=[
2009	-172.6827 58.2200 69326 263.2987
2010	-175.2373 59.5717 62362 249.7233
2012    -173.5880 59.2498 107720 328.2146
2014    -170.4699 58.1423 124130	352.3219
2016    -171.0219 58.1678 115180    339.3856
2018    -171.4704 58.5087 113180    336.4161    
2022    -172.8874 58.5449 121666 348.8072
];


%AT survey
[CGlonAT,CGlatAT]=m_ll2xy(CGI_ATsurvey(:,2),CGI_ATsurvey(:,3));  %convert x and y to m_map coords, then use these coords in plots
line1=plot(CGlonAT,CGlatAT,'--','Color',[0.25 0.25 0.25],'Marker','o');
text(CGlonAT+0.001,CGlatAT,num2str(CGI_ATsurvey(:,1)),'FontName','Times New Roman', 'FontSize',13, 'Color', [0.25 0.25 0.25])
hold on

%AVO-BT index
[CGlon1,CGlat1]=m_ll2xy(CGlon,CGlat);  %convert x and y to m_map coords, then use these coords in plots
line4=plot(CGlon1,CGlat1,'r-s','markersize',16);%,'MarkerFaceColor','k');
hold on
plot(CGlon1(end),CGlat1(end),'r-s','markersize',16,'markerfacecolor','r')
text(CGlon1+0.001,CGlat1,num2str(all_years'),'FontName','Times New Roman', 'FontSize',13,'Color','red')
legend([line1 line4],'AT survey','AVO','Location','Bestoutside')


set(gca,'FontSize',24)
orient portrait
pngfile=[output_path,'CGI ',num2str(all_years),'.png'];
print('-dpng','-r90',pngfile);