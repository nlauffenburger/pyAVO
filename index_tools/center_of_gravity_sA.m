function [CGlon,CGlat]=center_of_gravity_sA(lon,lat,sA)

%center_of_gravity_sA.m
%
%input lat, lon, sA 
%
%usage:  [CGlon,CGlat]=center_of_gravity_sA(input_x,input_y,input_z)
%see test import data at end of code
%
%assumes the area for which average sA is calculated is constant
%uses only valid grid cells

%take care of positive longitudes and make all neg west
temp=find(lon>0);  
lon(temp)=-(360-lon(temp));

%convert lat, lon to transformed coordinates using m_map
m_proj('Lambert Conformal Conic','longitudes',[-185 -155],'latitudes',[54 64]);   
[x,y]=m_ll2xy(lon,lat);

%compute center of gravity
% Changed the nansum out for 2022 because someone has the staitstics toolbox
% and I was impatient
nonan_ind_x = ~isnan(sA) & ~isnan(x);
nonan_ind_y = ~isnan(sA) & ~isnan(y);
CGx=sum(x(nonan_ind_x).*sA(nonan_ind_x))./sum(sA(nonan_ind_x));
CGy=sum(y(nonan_ind_y).*sA(nonan_ind_y))./sum(sA(nonan_ind_y));

%back-transform to lat, lon
[CGlon,CGlat]=m_xy2ll(CGx,CGy);

%test input data
% lon2=[-170 -170 -170 -170 -170 -170]';
% lat2=[60 61 62 63 64 65]';
% sA2=[100 100 100 100 100 100]';

% input_x=[-170 -169 -170 -169 -170 -169]';
% input_y=[60 60 60.2 60.2 60.4 60.4]';
% input_z=[100 100 100 100 100 100]';

% figure
% plot(input_x,input_y,'k.')
% hold on
% plot(CGlon2,CGlat2,'rx')



