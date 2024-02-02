%plot_log10INASC
% 
%outputs
% plot of x vs y with dot colormaped to intensity of z (z is log-10
% transformed in the code)
%
% inputs
%x - x coordinates %(e.g. longitude
%y - y coordinates %(ex. latitude)
%z - intensity %-e.g. sA
%marker_size - %size of marker e.g. 10 (only if scatter function is used,
%see revision notes below)
% 
%
%PHR 10/26/06 created this function based on colordot_adr.m (ADR and PHR) and
%plot_INASC.m (TBB and PHR)...makes a map of eastern Bering Sea
%
%PHR, May 2007: created log plot version
%
%PHR, March 2010:  change back to from use of scatter() to homebrew
%colorplot code.  Can't have scaled marker size.
%
%usage example:
%PHR_plot_log10INASC(x,y,z,4,[-1e-016 3.1])

function plot_log10INASC(x,y,z,marker_size,scale_limits)

%add some necessary directories to matlab path
%disp('if necessary, adding m_map directory from g to path so function can work')
if exist('m_map')==0
    addpath('G:\matlab\rht_toolbox\m_map')
end

%*****set up figure window with a map projection
%a1=axes;
a1=axes('position',[.11  .27  .8  .65]);  %set up axis for plot and keep handle
a1=gca;
m_proj('Lambert Conformal Conic','longitudes',[-180 -160],'latitudes',[54 63]);   

%plot 200m bathymetry contour
load 200mbathy
for u=1:length(selected_output)
    [b_proj,c_proj]=m_ll2xy(selected_output{1,u},selected_output{2,u});
    plot(b_proj,c_proj,'b-')
    hold on
end

m_grid('FontName','Times New Roman');


%load and plot coastline data in m_plot window
load EBS_nopoli
[coastlon_proj,coastlat_proj]=m_ll2xy(coastlon,coastlat);
plot(coastlon_proj,coastlat_proj, 'k');
xlabel('Longitude','FontName','Times New Roman')
ylabel('Latitude','FontName','Times New Roman')


%plot convention line if use EBS_nopoli above
load convention_line
m_plot(convention_line(:,2),convention_line(:,1),'k--')

[x,y]=m_ll2xy(x,y);  %convert x and y to m_map coords, then use these coords
                     %in further plotting
                     
%plot a small marker at each data location
%plot(x,y,'k.','MarkerSize',0.5)

z=log10(z+1);  %apply log transformation to data

%------------------------------------------------------------------
%color scaling:
    %construct colormap
    %colormap gray  %use this if you want b&w colormap
    %getcolormap=flipud(colormap);  %use this if you plot low points last
    colormap(jet)
    getcolormap=colormap;  %use this if you plot high points last
    %count=find(z>0);              %comment thexe lines and instead,
    %datamin=min(min(z(count)));   %use 0 as beginning of color scale, PHR
                                   %10/26/06

    %disp('using zero and max for color scale')
    %datamin=0
    %datamax=max(max(z))
    %comment out previous and insert code for constant color scale:
%     disp('use the following for color scale:');
    if exist('scale_limits')==1
        datamin=scale_limits(1);
        datamax=scale_limits(2);
    else
        %datamin=0
        datamin=-1e-016;  %use this instead of zero to make the color bar display zero
        %datamax=3.1  %2.8 for autokrill?  %3.1 for autopollock?
        datamax=4.1;  %4.1 for AVO nouveau 2009-2023
        %comment out previous and use 5th-95th percentile for color scale
        %disp('using 98th percentile as upper end of color scale')
        %datamin=0
        %datamax=prctile(z,98) 
    end

    dataincr=(datamax-datamin)/length(getcolormap);  %find increments for plotting
    
    %make custom colorbar on plot (this turned out to be non-trivial, since the normal
    %colorbar only works for patch, mesh, surf objects etc.
    a2=axes('position',[.1 .1  .8  .05]);  % colorbar axis
    C=datamin:dataincr:datamax;
    %C=10^(datamin):10^(dataincr):10^(datamax);  
    %C=0:10^(dataincr):10^(datamax);  %comment out previous line and use this
     
    imagesc(C,C,C)
    h=gca;
    %set(h,'Xscale','log')  %add this line
    set(h,'XTick',[0 1 2 3 4])
    set(h,'XTickLabel',[0 10 100 1000 10000])
    set(h,'YTickLabel',[])
    set(h,'FontName','Times New Roman')
%     set(h,'FontName','Arial')
    %xlabel('Log10 of sA(m^2/nmi^2)','FontName','Times New Roman')
    %xlabel('legend','FontName','Times New Roman')
        
%loop to plot color-coded points for increments of z; increments
%are based on the number of colors in getcolormap and the range of
%the data (see datamin, datamax, dataincr)
axes(a1);  %change from colorbar to axis of plot
hold on

for j=1:length(getcolormap) % for defaults, this is 64
        
%     %color increment for this loop.  this version plots high points first
%     datascale=datamax-j*dataincr;
%         
%     %find indices of suitable z data
%     if isequal(datascale+dataincr,datamax)==1
%         index=find(z>=datascale);   %PHR: this case necessary to make sure all points plotted
%                                     %in case of datamax~=max(z)  05/23/07
%     elseif isequal(datascale,datamin)==1
%         index=find(z<datascale+dataincr);   %PHR: this case necessary to make sure all points plotted
%                                             %in case of datamin~=0  05/23/07
%     else
%         index=find(z>=datascale & z<datascale+dataincr); % adr added >= so all plots are plotted
%     end
%     
%     %three dimensional scatterplot where the symbols are colored by the
%     %colors in getcolormap based on datascale and j
%     plot(x(index), y(index),'o','Color',getcolormap(j,:),'MarkerSize',marker_size)

    %color increment for this loop.  this version plots high points last,
    %so they are more visible
    datascale=datamin+j*dataincr;
        
    %find indices of suitable z data
    if isequal(datascale+dataincr,datamax)==1
        index=find(z>=datascale);   
    elseif isequal(datascale,datamin)==1
        index=find(z<datascale+dataincr);   
    else
        index=find(z<datascale & z>=datascale-dataincr); 
    end
    
    %three dimensional scatterplot where the symbols are colored by the
    %colors in getcolormap based on datascale and j
    plot(x(index),y(index),'o','Color',getcolormap(j,:),'MarkerSize',marker_size)

    
end
%
%
%
%code to use matlab function scatter() instead---------------------------------
%     disp('using zero and max for color scale')
%     datamin=0
%     datamax=max(max(z))
    %comment out previous and insert code for constant color scale:
    %disp('use the following for color scale:')
    %datamin=0
    %datamin=-1e-016  %use this instead of zero to make the color bar display zero
    %datamax=3.1  %2.8 for autokrill?  %3.1 for autopollock?
    %comment out previous and use 5th-95th percentile for color scale
%     disp('using 98th percentile as upper end of color scale')
%     datamin=0
%     datamax=prctile(z,98) 

%make plot using matlab function scatter()
%scatter(x,y,repmat(marker_size,length(z),1),z)


%title('title','FontName','Times New Roman')

% %color bar one way
% caxis([datamin datamax]) % set axis for plotting color
% colorbar('eastoutside','FontName','Times New Roman','ytick',([0 1 2 3]),...
%     'yticklabel',{'0','10','100','1000'})  % set axis limits to correspond to data_range
% 
% title('title','FontName','Times New Roman')

%color bar another way
%caxis([datamin datamax]) % set axis for plotting color
%colorbar('southoutside','FontName','Times New Roman','xtick',([0 1 2 3]),...
%    'xticklabel',{'0','10','100','1000'})  % set axis limits to correspond to data_range
%colorbar('southoutside','FontName','Times New Roman')
%title('title','FontName','Times New Roman')
%------------------------------------------
